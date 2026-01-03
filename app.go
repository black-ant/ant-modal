package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App struct
type App struct {
	ctx         context.Context
	projectsDir string
	logger      *log.Logger
	logFile     *os.File
	runningCmd  *exec.Cmd  // 当前运行的命令
	cmdMutex    sync.Mutex // 保护并发访问
}

// ModalApp Modal应用配置
type ModalApp struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	AppName     string    `json:"appName"` // Modal平台上的应用名称
	Description string    `json:"description"`
	Token       string    `json:"token"`       // Modal Token (兼容旧格式: token_id:token_secret)
	TokenID     string    `json:"tokenId"`     // Modal Token ID
	TokenSecret string    `json:"tokenSecret"` // Modal Token Secret
	Workspace   string    `json:"workspace"`   // Modal Workspace
	Suffix      string    `json:"suffix"`      // 应用名称后缀，用于多环境区分 (如 -test, -prod)
	CreatedAt   time.Time `json:"createdAt"`
	UpdatedAt   time.Time `json:"updatedAt"`
}

// Template 模板结构
type Template struct {
	Code        string   `json:"code"`        // 唯一标识 (如 "z-image-turbo")
	Name        string   `json:"name"`        // 显示名称
	Description string   `json:"description"` // 描述
	Category    string   `json:"category"`    // 分类
	Icon        string   `json:"icon"`        // 图标
	Tags        []string `json:"tags"`        // 标签
}

// Project 项目结构
type Project struct {
	Code         string            `json:"code"`         // 唯一标识代码 (用户可读，如 "my-project")
	ID           string            `json:"id"`           // 兼容旧版ID (将逐步废弃)
	Name         string            `json:"name"`         // 项目名称
	Path         string            `json:"path"`         // 兼容旧版路径 (将通过 code 计算)
	Description  string            `json:"description"`  // 描述
	TemplateCode string            `json:"templateCode"` // 来源模板代码
	AppID        string            `json:"appId"`        // 关联的 Modal App ID
	Status       string            `json:"status"`       // running, stopped, deploying
	Scripts      []Script          `json:"scripts"`      // 脚本列表
	Variables    map[string]string `json:"variables"`    // 项目级变量
	CreatedAt    time.Time         `json:"createdAt"`
	UpdatedAt    time.Time         `json:"updatedAt"`
}

// Script Modal脚本
type Script struct {
	Name        string `json:"name"`        // 显示名称（中文）
	Path        string `json:"path"`        // 相对路径
	FullPath    string `json:"fullPath"`    // 完整路径
	Description string `json:"description"` // 描述
	Order       int    `json:"order"`       // 排序序号
}

// CommandResult 命令执行结果
type CommandResult struct {
	Success bool   `json:"success"`
	Output  string `json:"output"`
	Error   string `json:"error"`
}

// ExecutionLog 执行日志
type ExecutionLog struct {
	ID            string            `json:"id"`            // 唯一标识
	ProjectID     string            `json:"projectId"`     // 项目 ID (兼容旧版，新项目使用 projectCode)
	ProjectCode   string            `json:"projectCode"`   // 项目代码
	ProjectName   string            `json:"projectName"`   // 项目名称
	ScriptName    string            `json:"scriptName"`    // 脚本名称
	ScriptPath    string            `json:"scriptPath"`    // 脚本路径
	ScriptContent string            `json:"scriptContent"` // 执行的完整脚本内容
	Command       string            `json:"command"`       // 执行命令 (deploy/run)
	Variables     map[string]string `json:"variables"`     // 填充的变量值
	StartTime     int64             `json:"startTime"`     // 开始时间戳
	EndTime       int64             `json:"endTime"`       // 结束时间戳
	Status        string            `json:"status"`        // 状态: running/success/failed
	Output        string            `json:"output"`        // 执行输出
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

// getExecutableDir 获取可执行文件所在目录
func (a *App) getExecutableDir() string {
	// 开发模式：使用当前工作目录
	if cwd, err := os.Getwd(); err == nil {
		// 检查是否在项目根目录（包含 wails.json）
		if _, err := os.Stat(filepath.Join(cwd, "wails.json")); err == nil {
			return cwd
		}
	}

	// 生产模式：使用可执行文件所在目录
	exePath, err := os.Executable()
	if err != nil {
		// 回退到当前工作目录
		if cwd, err := os.Getwd(); err == nil {
			return cwd
		}
		return "."
	}

	return filepath.Dir(exePath)
}

// getProjectAbsolutePath 获取项目的绝对路径（从相对路径计算）
func (a *App) getProjectAbsolutePath(relativePath string) string {
	// 如果已经是绝对路径，直接返回（兼容旧数据）
	if filepath.IsAbs(relativePath) {
		return relativePath
	}
	return filepath.Join(a.projectsDir, "projects", relativePath)
}

// getScriptAbsolutePath 获取脚本的绝对路径
func (a *App) getScriptAbsolutePath(projectRelativePath, scriptPath string) string {
	return filepath.Join(a.getProjectAbsolutePath(projectRelativePath), scriptPath)
}

// getProjectRelativePath 从绝对路径获取相对路径
func (a *App) getProjectRelativePath(absolutePath string) string {
	projectsBase := filepath.Join(a.projectsDir, "projects")
	if strings.HasPrefix(absolutePath, projectsBase) {
		rel, err := filepath.Rel(projectsBase, absolutePath)
		if err == nil {
			return rel
		}
	}
	// 如果无法计算相对路径，尝试只保留最后一部分（项目ID或名称）
	return filepath.Base(absolutePath)
}

// getProjectPathByCode 根据项目代码获取项目目录的绝对路径
func (a *App) getProjectPathByCode(code string) string {
	return filepath.Join(a.projectsDir, "projects", code)
}

// getTemplatesDir 获取模板目录的绝对路径
func (a *App) getTemplatesDir() string {
	return filepath.Join(a.projectsDir, "templates")
}

// GetTemplates 获取所有模板列表
func (a *App) GetTemplates() ([]Template, error) {
	templatesFile := filepath.Join(a.getTemplatesDir(), "templates.json")

	data, err := os.ReadFile(templatesFile)
	if err != nil {
		a.LogError(fmt.Sprintf("读取模板索引文件失败: %v", err))
		return nil, err
	}

	var result struct {
		Version   string     `json:"version"`
		Templates []Template `json:"templates"`
	}

	if err := json.Unmarshal(data, &result); err != nil {
		a.LogError(fmt.Sprintf("解析模板索引文件失败: %v", err))
		return nil, err
	}

	return result.Templates, nil
}

// GetTemplateByCode 根据代码获取模板
func (a *App) GetTemplateByCode(code string) (*Template, error) {
	templates, err := a.GetTemplates()
	if err != nil {
		return nil, err
	}

	for _, t := range templates {
		if t.Code == code {
			return &t, nil
		}
	}

	return nil, fmt.Errorf("模板不存在: %s", code)
}

// GetTemplateScripts 获取模板的脚本列表
func (a *App) GetTemplateScripts(templateCode string) ([]Script, error) {
	templateDir := filepath.Join(a.getTemplatesDir(), templateCode)

	if _, err := os.Stat(templateDir); os.IsNotExist(err) {
		return nil, fmt.Errorf("模板目录不存在: %s", templateCode)
	}

	var scripts []Script
	files, err := os.ReadDir(templateDir)
	if err != nil {
		return nil, err
	}

	for i, file := range files {
		if !file.IsDir() && strings.HasSuffix(file.Name(), ".py") {
			scripts = append(scripts, Script{
				Name:     file.Name(),
				Path:     file.Name(),
				FullPath: filepath.Join(templateDir, file.Name()),
				Order:    i,
			})
		}
	}

	return scripts, nil
}

// startup is called when the app starts
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	// 设置项目目录 - 使用项目根目录下的 data 目录
	rootDir := a.getExecutableDir()
	a.projectsDir = filepath.Join(rootDir, "data")

	// 创建数据目录
	if err := os.MkdirAll(a.projectsDir, 0755); err != nil {
		fmt.Printf("创建数据目录失败: %v\n", err)
	}

	// 初始化日志
	logPath := filepath.Join(a.projectsDir, "app.log")
	file, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0666)
	if err != nil {
		fmt.Printf("无法创建日志文件: %v\n", err)
	} else {
		a.logFile = file
		a.logger = log.New(file, "", log.LstdFlags)
	}

	a.LogInfo(fmt.Sprintf("应用启动，数据目录: %s", a.projectsDir))

	// 执行数据迁移：将旧的绝对路径转换为相对路径
	a.migrateAbsolutePathsToRelative()
}

// migrateAbsolutePathsToRelative 将旧的绝对路径转换为相对路径
func (a *App) migrateAbsolutePathsToRelative() {
	projects := a.GetProjects()
	if len(projects) == 0 {
		return
	}

	needsSave := false
	projectsBase := filepath.Join(a.projectsDir, "projects")

	for i := range projects {
		project := &projects[i]

		// 检查项目路径是否是绝对路径
		if filepath.IsAbs(project.Path) {
			// 尝试转换为相对路径
			if strings.HasPrefix(project.Path, projectsBase) {
				rel, err := filepath.Rel(projectsBase, project.Path)
				if err == nil {
					a.LogInfo(fmt.Sprintf("迁移项目路径: %s -> %s", project.Path, rel))
					project.Path = rel
					needsSave = true
				}
			} else {
				// 如果不在 projects 目录下，使用目录名作为相对路径
				project.Path = filepath.Base(project.Path)
				needsSave = true
			}
		}

		// 清空脚本的 FullPath（运行时动态计算）
		for j := range project.Scripts {
			if project.Scripts[j].FullPath != "" {
				project.Scripts[j].FullPath = ""
				needsSave = true
			}
		}
	}

	// 如果有修改，保存项目配置
	if needsSave {
		if err := a.SaveProjects(projects); err != nil {
			a.LogError(fmt.Sprintf("迁移数据保存失败: %v", err))
		} else {
			a.LogInfo("项目路径迁移完成：已将绝对路径转换为相对路径")
		}
	}
}

// shutdown cleanup resources
func (a *App) shutdown(ctx context.Context) {
	if a.logFile != nil {
		a.logFile.Close()
	}
}

// LogType 日志类型
type LogType string

const (
	LogTypeInfo    LogType = "info"
	LogTypeError   LogType = "error"
	LogTypeWarning LogType = "warning"
	LogTypeCommand LogType = "command"
)

// LogEntry 日志条目
type LogEntry struct {
	Timestamp string  `json:"timestamp"`
	Type      LogType `json:"type"`
	Message   string  `json:"message"`
}

// Log 记录日志并发送到前端
func (a *App) Log(lType LogType, message string) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")

	// 写入文件
	if a.logger != nil {
		prefix := fmt.Sprintf("[%s] [%s] ", timestamp, lType)
		a.logger.SetPrefix(prefix)
		a.logger.Println(message)
	}

	// 打印到控制台 (开发调试用)
	fmt.Printf("[%s] %s: %s\n", timestamp, lType, message)

	// 发送到前端
	if a.ctx != nil {
		runtime.EventsEmit(a.ctx, "log:entry", LogEntry{
			Timestamp: timestamp,
			Type:      lType,
			Message:   message,
		})
	}
}

// LogInfo 记录信息日志
func (a *App) LogInfo(message string) {
	a.Log(LogTypeInfo, message)
}

// LogError 记录错误日志
func (a *App) LogError(message string) {
	a.Log(LogTypeError, message)
}

// LogWarning 记录警告日志
func (a *App) LogWarning(message string) {
	a.Log(LogTypeWarning, message)
}

// getModalPath 获取 modal 命令的完整路径
func (a *App) getModalPath() string {
	// 首先尝试直接使用 modal
	if path, err := exec.LookPath("modal"); err == nil {
		return path
	}

	// 尝试常见的 Python Scripts 路径
	homeDir, _ := os.UserHomeDir()
	possiblePaths := []string{
		filepath.Join(homeDir, "AppData", "Local", "Programs", "Python", "Python311", "Scripts", "modal.exe"),
		filepath.Join(homeDir, "AppData", "Local", "Programs", "Python", "Python310", "Scripts", "modal.exe"),
		filepath.Join(homeDir, "AppData", "Local", "Programs", "Python", "Python39", "Scripts", "modal.exe"),
		filepath.Join(homeDir, "AppData", "Roaming", "Python", "Python311", "Scripts", "modal.exe"),
		filepath.Join(homeDir, "AppData", "Roaming", "Python", "Python310", "Scripts", "modal.exe"),
		filepath.Join(homeDir, ".local", "bin", "modal"), // Linux/Mac
		"/usr/local/bin/modal", // Mac
	}

	for _, p := range possiblePaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	// 如果都找不到，返回 modal 让系统尝试
	return "modal"
}

// GetProjects 获取所有项目
func (a *App) GetProjects() []Project {
	fmt.Println("DEBUG: GetProjects called")
	projects := []Project{}
	configPath := filepath.Join(a.projectsDir, "projects.json")
	fmt.Printf("DEBUG: Reading projects from %s\n", configPath)

	data, err := os.ReadFile(configPath)
	if err != nil {
		fmt.Printf("DEBUG: Failed to read file: %v\n", err)
		return projects
	}

	fmt.Printf("DEBUG: File content size: %d bytes\n", len(data))
	if len(data) > 0 {
		fmt.Printf("DEBUG: File content start: %s\n", string(data[:min(100, len(data))]))
	}

	if err := json.Unmarshal(data, &projects); err != nil {
		fmt.Printf("DEBUG: JSON Unmarshal error: %v\n", err)
		return projects
	}

	fmt.Printf("DEBUG: Successfully loaded %d projects\n", len(projects))
	return projects
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// SaveProjects 保存项目列表
func (a *App) SaveProjects(projects []Project) error {
	configPath := filepath.Join(a.projectsDir, "projects.json")
	data, err := json.MarshalIndent(projects, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(configPath, data, 0644)
}

// CreateProject 创建新项目
func (a *App) CreateProject(name, path, description, appId string) (*Project, error) {
	a.LogInfo(fmt.Sprintf("[CreateProject] 开始创建项目: name=%s, path=%s, appId=%s", name, path, appId))

	projects := a.GetProjects()

	projectID := fmt.Sprintf("%d", time.Now().UnixNano())

	// 存储相对路径，运行时动态计算绝对路径
	var relativePath string
	if path == "" {
		// 使用项目ID作为相对路径
		relativePath = projectID
		// 创建项目目录（使用绝对路径）
		absolutePath := a.getProjectAbsolutePath(relativePath)
		a.LogInfo(fmt.Sprintf("[CreateProject] 创建项目目录: %s", absolutePath))
		if err := os.MkdirAll(absolutePath, 0755); err != nil {
			a.LogError(fmt.Sprintf("[CreateProject] 创建目录失败: path=%s, error=%v", absolutePath, err))
			return nil, fmt.Errorf("创建项目目录失败: %v", err)
		}
	} else {
		// 如果提供了路径，转换为相对路径
		relativePath = a.getProjectRelativePath(path)
		a.LogInfo(fmt.Sprintf("[CreateProject] 使用现有路径: %s -> %s", path, relativePath))
	}

	project := Project{
		ID:          projectID,
		Name:        name,
		Path:        relativePath, // 存储相对路径
		Description: description,
		AppID:       appId,
		Status:      "stopped",
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	projects = append(projects, project)
	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[CreateProject] 保存项目配置失败: %v", err))
		return nil, err
	}

	a.LogInfo(fmt.Sprintf("[CreateProject] 项目创建成功: id=%s, name=%s", projectID, name))
	return &project, nil
}

// DeleteProject 删除项目
func (a *App) DeleteProject(id string) error {
	a.LogInfo(fmt.Sprintf("[DeleteProject] 开始删除项目: id=%s", id))

	projects := a.GetProjects()
	newProjects := []Project{}
	var deletedProject *Project

	for _, p := range projects {
		if p.ID != id {
			newProjects = append(newProjects, p)
		} else {
			deletedProject = &p
		}
	}

	if deletedProject == nil {
		a.LogWarning(fmt.Sprintf("[DeleteProject] 项目不存在: id=%s", id))
	} else {
		a.LogInfo(fmt.Sprintf("[DeleteProject] 找到项目: name=%s, path=%s", deletedProject.Name, deletedProject.Path))
	}

	if err := a.SaveProjects(newProjects); err != nil {
		a.LogError(fmt.Sprintf("[DeleteProject] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[DeleteProject] 项目删除成功: id=%s", id))
	return nil
}

// UpdateProject 更新项目信息
func (a *App) UpdateProject(id, name, description, appId string) error {
	a.LogInfo(fmt.Sprintf("[UpdateProject] 开始更新项目: id=%s, name=%s, appId=%s", id, name, appId))

	projects := a.GetProjects()
	found := false

	for i, p := range projects {
		if p.ID == id {
			projects[i].Name = name
			projects[i].Description = description
			projects[i].AppID = appId
			projects[i].UpdatedAt = time.Now()
			found = true
			break
		}
	}

	if !found {
		a.LogError(fmt.Sprintf("[UpdateProject] 更新失败: 项目不存在, id=%s", id))
		return fmt.Errorf("项目不存在")
	}

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[UpdateProject] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[UpdateProject] 项目更新成功: id=%s, name=%s", id, name))
	return nil
}

// GetProjectVariables 获取项目变量
func (a *App) GetProjectVariables(projectId string) map[string]string {
	projects := a.GetProjects()
	for _, p := range projects {
		if p.ID == projectId {
			if p.Variables == nil {
				return make(map[string]string)
			}
			return p.Variables
		}
	}
	return make(map[string]string)
}

// SetProjectVariables 设置项目变量
func (a *App) SetProjectVariables(projectId string, variables map[string]string) error {
	a.LogInfo(fmt.Sprintf("[SetProjectVariables] 设置项目变量: projectId=%s, count=%d", projectId, len(variables)))

	projects := a.GetProjects()
	found := false

	for i, p := range projects {
		if p.ID == projectId {
			projects[i].Variables = variables
			projects[i].UpdatedAt = time.Now()
			found = true
			break
		}
	}

	if !found {
		return fmt.Errorf("项目不存在")
	}

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[SetProjectVariables] 保存失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[SetProjectVariables] 项目变量设置成功: projectId=%s", projectId))
	return nil
}

// GetGlobalVariables 获取全局变量
func (a *App) GetGlobalVariables() map[string]string {
	variables := make(map[string]string)
	configPath := filepath.Join(a.projectsDir, "global_variables.json")

	data, err := os.ReadFile(configPath)
	if err != nil {
		return variables
	}

	json.Unmarshal(data, &variables)
	return variables
}

// SetGlobalVariables 设置全局变量
func (a *App) SetGlobalVariables(variables map[string]string) error {
	a.LogInfo(fmt.Sprintf("[SetGlobalVariables] 设置全局变量: count=%d", len(variables)))

	configPath := filepath.Join(a.projectsDir, "global_variables.json")
	data, err := json.MarshalIndent(variables, "", "  ")
	if err != nil {
		a.LogError(fmt.Sprintf("[SetGlobalVariables] 序列化失败: %v", err))
		return err
	}

	if err := os.WriteFile(configPath, data, 0644); err != nil {
		a.LogError(fmt.Sprintf("[SetGlobalVariables] 写入失败: %v", err))
		return err
	}

	a.LogInfo("[SetGlobalVariables] 全局变量设置成功")
	return nil
}

// CreateProjectFromTemplate 从模板创建项目
func (a *App) CreateProjectFromTemplate(templateId, projectName, appId string) (*Project, error) {
	a.LogInfo(fmt.Sprintf("[TemplateCreate] 开始从模板创建项目: templateId=%s, projectName=%s, appId=%s", templateId, projectName, appId))

	// 生成项目ID（同时作为相对路径）
	projectID := fmt.Sprintf("%d", time.Now().UnixNano())
	// 绝对路径用于创建目录和复制文件
	projectAbsPath := a.getProjectAbsolutePath(projectID)

	a.LogInfo(fmt.Sprintf("[TemplateCreate] 项目路径: id=%s, absPath=%s", projectID, projectAbsPath))

	// 创建项目目录
	if err := os.MkdirAll(projectAbsPath, 0755); err != nil {
		a.LogError(fmt.Sprintf("[TemplateCreate] 创建项目目录失败: path=%s, error=%v", projectAbsPath, err))
		return nil, fmt.Errorf("创建项目目录失败: %v", err)
	}

	a.LogInfo(fmt.Sprintf("[TemplateCreate] 项目目录创建成功: %s", projectAbsPath))

	// 根据模板ID复制脚本文件
	var scripts []Script
	var description string

	a.LogInfo(fmt.Sprintf("[TemplateCreate] 开始复制模板文件: templateId=%s", templateId))

	switch templateId {
	case "stable-diffusion":
		description = "使用 SDXL 模型生成高质量图像，支持电商产品图、社媒营销图等业务场景"
		scripts = a.copyStableDiffusionTemplate(projectAbsPath)
	case "ai-llm":
		description = "一站式大模型部署，支持 Llama/Qwen/ChatGLM/Mistral/Yi/DeepSeek 等主流模型"
		scripts = a.copyAILLMTemplate(projectAbsPath)
	case "whisper-stt":
		description = "使用 OpenAI Whisper 进行语音转文字，支持会议纪要、字幕生成等场景"
		scripts = a.copyWhisperSTTTemplate(projectAbsPath)
	case "embedding-service":
		description = "生成文本向量，支持企业知识库检索、商品推荐等业务场景"
		scripts = a.copyEmbeddingServiceTemplate(projectAbsPath)
	case "lora-training":
		description = "使用 LoRA 技术微调 Stable Diffusion 模型"
		scripts = a.copyLoRATrainingTemplate(projectAbsPath)
	case "redis-server":
		description = "在 Modal 上部署持久化的 Redis 服务器，支持 AOF + RDB 双重持久化"
		scripts = a.copyRedisServerTemplate(projectAbsPath)
	case "comfyui-node-manager":
		description = "完整的 ComfyUI 部署和管理方案：安装应用、添加模型、管理节点"
		scripts = a.copyComfyUINodeManagerTemplate(projectAbsPath)
	case "postgresql-server":
		description = "部署持久化 PostgreSQL 数据库，支持复杂查询和事务"
		scripts = a.copyPostgreSQLTemplate(projectAbsPath)
	case "mongodb-server":
		description = "部署 MongoDB 文档数据库，灵活的 JSON 存储"
		scripts = a.copyMongoDBTemplate(projectAbsPath)
	case "minio-storage":
		description = "部署 S3 兼容的对象存储服务，适合文件存储"
		scripts = a.copyMinIOTemplate(projectAbsPath)
	case "image-classification":
		description = "使用 ViT/ResNet 进行图像分类，商品分类和内容审核"
		scripts = a.copyImageClassificationTemplate(projectAbsPath)
	case "ocr-service":
		description = "使用 EasyOCR 识别图片中的文字，支持中英文"
		scripts = a.copyOCRServiceTemplate(projectAbsPath)
	case "sentiment-analysis":
		description = "分析文本情感倾向，适合评论分析和舆情监控"
		scripts = a.copySentimentAnalysisTemplate(projectAbsPath)
	case "rabbitmq-server":
		description = "部署消息队列服务，支持异步任务和服务解耦"
		scripts = a.copyRabbitMQTemplate(projectAbsPath)
	case "celery-tasks":
		description = "分布式任务队列，支持异步任务和定时任务"
		scripts = a.copyCeleryTasksTemplate(projectAbsPath)
	case "api-gateway":
		description = "统一 API 入口，支持限流、认证、路由转发"
		scripts = a.copyAPIGatewayTemplate(projectAbsPath)
	case "modal-basics":
		description = "从零开始学习 Modal，包含 14 个循序渐进的实战案例：基础功能 + 真实业务场景"
		scripts = a.copyModalBasicsTemplate(projectAbsPath)
	case "z-image-turbo":
		description = "阿里巴巴 Z-Image-Turbo 高效图像生成，6B 参数媲美 20B+ 模型，擅长照片级真实人像"
		scripts = a.copyZImageTurboTemplate(projectAbsPath)
	case "wan21-t2v":
		description = "Wan 2.1 文生视频 (Text-to-Video)，阿里巴巴开源视频生成模型，支持 14B/1.3B 参数"
		scripts = a.copyWan21T2VTemplate(projectAbsPath)
	default:
		a.LogError(fmt.Sprintf("[TemplateCreate] 未知的模板ID: %s", templateId))
		return nil, fmt.Errorf("未知的模板ID: %s", templateId)
	}

	a.LogInfo(fmt.Sprintf("[TemplateCreate] 模板文件复制完成: 脚本数量=%d", len(scripts)))

	// 创建项目（存储相对路径）
	project := Project{
		ID:          projectID,
		Name:        projectName,
		Path:        projectID, // 存储相对路径（即项目ID）
		Description: description,
		AppID:       appId,
		Status:      "stopped",
		Scripts:     scripts,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	// 保存项目
	projects := a.GetProjects()
	projects = append(projects, project)
	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[TemplateCreate] 保存项目配置失败: %v", err))
		return nil, err
	}

	a.LogInfo(fmt.Sprintf("[TemplateCreate] 项目创建成功: id=%s, name=%s, scripts=%d", projectID, projectName, len(scripts)))
	return &project, nil
}

// copyStableDiffusionTemplate 复制 Stable Diffusion 模板
func (a *App) copyStableDiffusionTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "stable-diffusion")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 Stable Diffusion 模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"SD 图像生成服务", "sd_service.py", "Stable Diffusion XL 基础图像生成服务"},
		{"电商产品图批量生成", "sd_ecommerce_product.py", "解决：为每个产品生成多种风格展示图，提升上新效率"},
		{"社媒营销图生成", "sd_social_media.py", "解决：运营每天需要大量配图，一键生成多平台尺寸"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] Stable Diffusion 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyAILLMTemplate 复制 AI 大模型模板
func (a *App) copyAILLMTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "ai-llm")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 AI LLM 模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"Llama 3 对话服务", "llama_service.py", "Meta Llama 3 模型，通用对话和问答"},
		{"Qwen 通义千问", "qwen_service.py", "阿里通义千问，中文能力强"},
		{"ChatGLM 智谱", "chatglm_service.py", "智谱 GLM-4，优秀中文理解"},
		{"Mistral/Mixtral", "mistral_service.py", "Mistral 高性能推理，MoE 架构"},
		{"Yi 零一万物", "yi_service.py", "零一万物 Yi，支持超长上下文"},
		{"DeepSeek 翻译", "deepseek_service.py", "DeepSeek V3 翻译服务"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] AI LLM 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyWhisperSTTTemplate 复制 Whisper 语音识别模板
func (a *App) copyWhisperSTTTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "whisper-stt")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 Whisper STT 模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"Whisper 语音识别", "whisper_service.py", "基础语音转文字服务"},
		{"会议纪要自动生成", "whisper_meeting_minutes.py", "解决：每次会议后整理纪要耗时 2 小时且容易遗漏"},
		{"视频字幕自动生成", "whisper_subtitle.py", "解决：手动添加字幕每小时视频需要 4-6 小时"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] Whisper 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyEmbeddingServiceTemplate 复制文本嵌入模板
func (a *App) copyEmbeddingServiceTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "embedding-service")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 Embedding 模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"文本嵌入服务", "embedding_service.py", "基础文本向量化和语义搜索"},
		{"企业知识库检索", "embedding_knowledge_base.py", "解决：传统关键词搜索找不到语义相关的文档内容"},
		{"相似商品推荐", "embedding_similar_product.py", "解决：用户描述需求后无法匹配到相似商品"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] Embedding 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyLoRATrainingTemplate 复制 LoRA 训练模板
func (a *App) copyLoRATrainingTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "lora-training")
	return a.copySingleScript(sourceDir, projectPath, "lora_training.py", "LoRA 训练服务", "LoRA 模型训练和推理")
}

// copySingleScript 辅助函数：复制单个脚本
func (a *App) copySingleScript(sourceDir, projectPath, fileName, name, desc string) []Script {
	scripts := []Script{}
	sourcePath := filepath.Join(sourceDir, fileName)
	destPath := filepath.Join(projectPath, fileName)

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制文件: %s -> %s", sourcePath, destPath))

	if data, err := os.ReadFile(sourcePath); err == nil {
		if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
			a.LogError(fmt.Sprintf("[TemplateCopy] 写入文件失败: %s, error=%v", destPath, writeErr))
		} else {
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 文件复制成功: %s (%d字节)", fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        name,
				Path:        fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: desc,
				Order:       0,
			})
		}
	} else {
		a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
	}

	return scripts
}

// copyRedisServerTemplate 复制 Redis 服务器模板
func (a *App) copyRedisServerTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "redis-server")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 Redis 服务器模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"Redis 服务器", "redis_server.py", "部署 Redis 服务器，数据持久化到 Volume"},
		{"Redis 客户端", "redis_client.py", "演示如何连接和使用 Redis 的各种功能"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		// 复制文件
		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] Redis 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyComfyUINodeManagerTemplate 复制 ComfyUI 节点管理器模板
func (a *App) copyComfyUINodeManagerTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "comfyui-node-manager")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 ComfyUI 节点管理器模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"1. 部署 ComfyUI", "comfyui_app.py", "部署完整 ComfyUI 服务（首次使用先运行此脚本）"},
		{"2. 添加节点", "add_custom_nodes.py", "安装/更新/删除自定义节点"},
		{"3. 添加模型", "add_models.py", "从 HuggingFace 或 URL 下载模型"},
		{"4. 诊断检查", "diagnose.py", "检查 Volume 中的节点和模型状态"},
		{"5. 重启服务", "restart_service.py", "重启 ComfyUI 以加载新添加的资源"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		// 复制文件
		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] ComfyUI 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyModalBasicsTemplate 复制 Modal 入门教程模板
func (a *App) copyModalBasicsTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "modal-basics")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 Modal 入门教程模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"01 - Hello Modal", "01_hello_modal.py", "最简单的云函数调用，理解 Modal 基本概念"},
		{"02 - 并行计算", "02_parallel_computing.py", "学习如何并行处理任务，体验云计算的性能优势"},
		{"03 - Web API", "03_web_api.py", "将函数暴露为 HTTP API，构建 Web 服务"},
		{"04 - 数据持久化", "04_volume_storage.py", "使用 Volume 持久化存储数据，实现文件读写"},
		{"05 - 定时任务", "05_scheduled_tasks.py", "设置定时任务，自动化执行周期性工作"},
		{"06 - GPU 计算", "06_gpu_computing.py", "使用 GPU 加速计算，对比 CPU 和 GPU 性能"},
		{"07 - 电商销售报表", "07_ecommerce_report.py", "解决：每天手动统计销售数据耗时易错，自动化生成日报"},
		{"08 - 网站可用性监控", "08_website_monitor.py", "解决：网站宕机无法及时发现，24/7 自动监控告警"},
		{"09 - 批量图片水印", "09_image_watermark.py", "解决：大量图片需要添加版权水印，本地处理太慢"},
		{"10 - 竞品价格监控", "10_price_tracker.py", "解决：竞争对手调价后不能及时发现，错失反应时机"},
		{"11 - 日志分析异常检测", "11_log_analyzer.py", "解决：海量服务器日志中发现问题如大海捞针"},
		{"12 - 短链接追踪服务", "12_url_shortener.py", "解决：营销链接太长且无法追踪点击效果"},
		{"13 - PDF 批量处理", "13_pdf_processor.py", "解决：HR/财务需要批量合并、拆分、加水印 PDF"},
		{"14 - 多渠道通知服务", "14_notification_service.py", "解决：活动期间需要快速发送大量用户通知"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		// 复制文件
		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "", // 不再存储绝对路径，运行时动态计算
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] Modal 入门教程模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyPostgreSQLTemplate 复制 PostgreSQL 模板
func (a *App) copyPostgreSQLTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "postgresql-server")
	return a.copySingleScript(sourceDir, projectPath, "postgres_service.py", "PostgreSQL 服务", "部署 PostgreSQL 数据库服务")
}

// copyMongoDBTemplate 复制 MongoDB 模板
func (a *App) copyMongoDBTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "mongodb-server")
	return a.copySingleScript(sourceDir, projectPath, "mongodb_service.py", "MongoDB 服务", "部署 MongoDB 数据库服务")
}

// copyMinIOTemplate 复制 MinIO 模板
func (a *App) copyMinIOTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "minio-storage")
	return a.copySingleScript(sourceDir, projectPath, "minio_service.py", "MinIO 存储服务", "部署 MinIO 对象存储")
}

// copyImageClassificationTemplate 复制图像分类模板
func (a *App) copyImageClassificationTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "image-classification")
	return a.copySingleScript(sourceDir, projectPath, "image_classifier.py", "图像分类服务", "使用 ViT 进行图像分类")
}

// copyOCRServiceTemplate 复制 OCR 模板
func (a *App) copyOCRServiceTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "ocr-service")
	return a.copySingleScript(sourceDir, projectPath, "ocr_service.py", "OCR 识别服务", "图片文字识别")
}

// copySentimentAnalysisTemplate 复制情感分析模板
func (a *App) copySentimentAnalysisTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "sentiment-analysis")
	return a.copySingleScript(sourceDir, projectPath, "sentiment_service.py", "情感分析服务", "分析文本情感（正面/负面）")
}

// copyRabbitMQTemplate 复制 RabbitMQ 模板
func (a *App) copyRabbitMQTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "rabbitmq-server")
	return a.copySingleScript(sourceDir, projectPath, "rabbitmq_service.py", "RabbitMQ 服务", "部署 RabbitMQ 消息队列")
}

// copyCeleryTasksTemplate 复制 Celery 模板
func (a *App) copyCeleryTasksTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "celery-tasks")
	return a.copySingleScript(sourceDir, projectPath, "celery_service.py", "Celery 任务服务", "分布式任务处理")
}

// copyAPIGatewayTemplate 复制 API 网关模板
func (a *App) copyAPIGatewayTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "api-gateway")
	return a.copySingleScript(sourceDir, projectPath, "gateway_service.py", "API 网关服务", "统一 API 入口和流量控制")
}

// copyZImageTurboTemplate 复制 Z-Image-Turbo 模板
func (a *App) copyZImageTurboTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "z-image-turbo")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 Z-Image-Turbo 模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"1. Z-Image 主服务", "z_image_app.py", "【首次部署】ComfyUI + 热加载 API，配置项目变量后部署"},
		{"2. 添加模型 (HuggingFace)", "add_model_hf.py", "从 HuggingFace 下载模型到共享 Volume"},
		{"3. 添加模型 (URL)", "add_model_url.py", "从 URL 直接下载模型到共享 Volume"},
		{"4. 模型管理", "manage_models.py", "列出/删除共享 Volume 中的模型"},
		{"5. 诊断工具", "diagnose.py", "检查共享 Volume 和服务状态"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "",
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] Z-Image-Turbo 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// copyWan21T2VTemplate 复制 Wan 2.1 T2V 模板
func (a *App) copyWan21T2VTemplate(projectPath string) []Script {
	sourceDir := filepath.Join(a.projectsDir, "templates", "wan21-t2v")
	scripts := []Script{}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制 Wan 2.1 T2V 模板: sourceDir=%s", sourceDir))

	files := []struct {
		name     string
		fileName string
		desc     string
	}{
		{"Wan 2.1 T2V 部署", "wan21_t2v_deploy.py", "【一键部署】Wan 2.1 文生视频服务，支持 14B/1.3B 模型"},
	}

	for i, f := range files {
		sourcePath := filepath.Join(sourceDir, f.fileName)
		destPath := filepath.Join(projectPath, f.fileName)

		if data, err := os.ReadFile(sourcePath); err == nil {
			if writeErr := os.WriteFile(destPath, data, 0644); writeErr != nil {
				a.LogError(fmt.Sprintf("[TemplateCopy] 写入失败: %s, error=%v", destPath, writeErr))
				continue
			}
			a.LogInfo(fmt.Sprintf("[TemplateCopy] 复制成功: %s (%d字节)", f.fileName, len(data)))
			scripts = append(scripts, Script{
				Name:        f.name,
				Path:        f.fileName,
				FullPath:    "",
				Description: f.desc,
				Order:       i,
			})
		} else {
			a.LogError(fmt.Sprintf("[TemplateCopy] 读取源文件失败: %s, error=%v", sourcePath, err))
		}
	}

	a.LogInfo(fmt.Sprintf("[TemplateCopy] Wan 2.1 T2V 模板复制完成: %d个文件", len(scripts)))
	return scripts
}

// GetScripts 获取项目中的所有Python脚本
func (a *App) GetScripts(projectPath string) []Script {
	// 计算项目的绝对路径
	projectAbsPath := a.getProjectAbsolutePath(projectPath)
	a.LogInfo(fmt.Sprintf("[GetScripts] projectPath=%s, projectAbsPath=%s", projectPath, projectAbsPath))

	// 首先从 projects.json 读取已配置的脚本
	projects := a.GetProjects()
	var configuredScripts []Script
	for i := range projects {
		if projects[i].Path == projectPath {
			configuredScripts = projects[i].Scripts
			a.LogInfo(fmt.Sprintf("[GetScripts] 找到项目配置, 已配置脚本数量=%d", len(configuredScripts)))
			break
		}
	}

	// 创建已配置脚本的路径集合（用于去重）
	configuredPaths := make(map[string]bool)
	for _, script := range configuredScripts {
		configuredPaths[script.Path] = true
	}

	// 验证已配置的脚本，动态计算 FullPath
	validScripts := []Script{}
	for i, script := range configuredScripts {
		fullPath := filepath.Join(projectAbsPath, script.Path)
		if _, err := os.Stat(fullPath); err == nil {
			script.FullPath = fullPath
			script.Order = i
			validScripts = append(validScripts, script)
		}
	}
	a.LogInfo(fmt.Sprintf("[GetScripts] 已配置的有效脚本数量=%d", len(validScripts)))

	// 扫描文件系统，查找未配置的新脚本
	newScriptsCount := 0
	filepath.Walk(projectAbsPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if !info.IsDir() && strings.HasSuffix(info.Name(), ".py") {
			relPath, _ := filepath.Rel(projectAbsPath, path)
			// 只添加未配置的脚本
			if !configuredPaths[relPath] {
				a.LogInfo(fmt.Sprintf("[GetScripts] 发现新脚本: %s", relPath))
				newScriptsCount++
				validScripts = append(validScripts, Script{
					Name:        info.Name(),
					Path:        relPath,
					FullPath:    path,
					Description: "",
					Order:       len(validScripts),
				})
			}
		}
		return nil
	})
	a.LogInfo(fmt.Sprintf("[GetScripts] 新发现的脚本数量=%d, 总脚本数量=%d", newScriptsCount, len(validScripts)))

	return validScripts
}

// RunModalCommand 执行Modal命令
func (a *App) RunModalCommand(command string, args []string, workDir string) CommandResult {
	cmdStr := fmt.Sprintf("modal %s %s", command, strings.Join(args, " "))
	a.Log(LogTypeCommand, fmt.Sprintf("执行命令: %s", cmdStr))

	// 发送开始事件
	runtime.EventsEmit(a.ctx, "command:start", command)

	modalPath := a.getModalPath()
	cmd := exec.Command(modalPath, append([]string{command}, args...)...)
	if workDir != "" {
		// 将相对路径转换为绝对路径
		cmd.Dir = a.getProjectAbsolutePath(workDir)
	}

	// 设置 UTF-8 编码，避免 Windows GBK 编码问题
	env := os.Environ()
	env = append(env, "PYTHONIOENCODING=utf-8")
	cmd.Env = env

	output, err := cmd.CombinedOutput()

	result := CommandResult{
		Success: err == nil,
		Output:  string(output),
	}

	if err != nil {
		result.Error = err.Error()
		a.LogError(fmt.Sprintf("命令执行失败: %s, 错误: %s, 输出: %s", cmdStr, err.Error(), string(output)))
	} else {
		a.LogInfo(fmt.Sprintf("命令执行成功: %s", cmdStr))
	}

	// 发送完成事件
	runtime.EventsEmit(a.ctx, "command:complete", result)

	return result
}

// DeployScript 部署脚本
func (a *App) DeployScript(scriptPath string, workDir string) CommandResult {
	// 查找项目并获取关联的 Modal App Token
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)
	return a.RunModalCommandWithEnv("deploy", []string{scriptPath}, workDir, tokenId, tokenSecret)
}

// DeployScriptWithContent 使用指定内容部署脚本（用于模板脚本变量替换后执行）
func (a *App) DeployScriptWithContent(scriptPath string, workDir string, content string) CommandResult {
	// 将相对路径转换为绝对路径
	workDirAbs := a.getProjectAbsolutePath(workDir)

	// 创建临时文件存放替换变量后的内容
	// 注意：Modal 不允许文件名包含多个点号，所以使用下划线前缀而不是点号
	tempFile := filepath.Join(workDirAbs, "_temp_"+filepath.Base(scriptPath))

	// 写入临时文件
	if err := os.WriteFile(tempFile, []byte(content), 0644); err != nil {
		return CommandResult{
			Success: false,
			Output:  "",
			Error:   fmt.Sprintf("创建临时文件失败: %v", err),
		}
	}

	// 确保在函数结束后删除临时文件
	defer os.Remove(tempFile)

	// 查找项目并获取关联的 Modal App Token
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)

	// 使用临时文件执行
	return a.RunModalCommandWithEnv("deploy", []string{filepath.Base(tempFile)}, workDir, tokenId, tokenSecret)
}

// RunScript 运行脚本
func (a *App) RunScript(scriptPath string, workDir string) CommandResult {
	// 查找项目并获取关联的 Modal App Token
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)
	return a.RunModalCommandWithEnv("run", []string{scriptPath}, workDir, tokenId, tokenSecret)
}

// ExecuteModalCommand 执行 Modal CLI 命令（用于快捷操作）
func (a *App) ExecuteModalCommand(fullCommand string) (string, error) {
	return a.ExecuteModalCommandWithToken(fullCommand, "", "")
}

// ExecuteModalCommandWithToken 执行带 Token 的 Modal CLI 命令
func (a *App) ExecuteModalCommandWithToken(fullCommand, tokenId, tokenSecret string) (string, error) {
	a.Log(LogTypeCommand, fmt.Sprintf("快捷操作执行: %s", fullCommand))

	// 解析命令，移除 "modal " 前缀
	cmdStr := strings.TrimPrefix(fullCommand, "modal ")
	parts := strings.Fields(cmdStr)

	if len(parts) == 0 {
		return "", fmt.Errorf("命令不能为空")
	}

	modalPath := a.getModalPath()
	cmd := exec.Command(modalPath, parts...)

	// 设置环境变量
	env := os.Environ()
	env = append(env, "PYTHONIOENCODING=utf-8")

	// 如果提供了 Token，设置环境变量
	if tokenId != "" && tokenSecret != "" {
		env = append(env, "MODAL_TOKEN_ID="+tokenId)
		env = append(env, "MODAL_TOKEN_SECRET="+tokenSecret)
		a.LogInfo(fmt.Sprintf("使用 Token ID: %s...", tokenId[:min(8, len(tokenId))]))
	}
	cmd.Env = env

	output, err := cmd.CombinedOutput()
	outputStr := string(output)

	if err != nil {
		a.LogError(fmt.Sprintf("命令执行失败: %v, 输出: %s", err, outputStr))
		return outputStr, fmt.Errorf("%s", outputStr)
	}

	a.LogInfo(fmt.Sprintf("命令执行成功: %s", cmdStr))
	return outputStr, nil
}

// getTokenForProjectPath 根据项目路径获取关联的 Token
func (a *App) getTokenForProjectPath(projectPath string) (string, string) {
	projects := a.GetProjects()
	for _, project := range projects {
		if project.Path == projectPath {
			if project.AppID != "" {
				app := a.GetModalAppByID(project.AppID)
				if app != nil {
					return app.TokenID, app.TokenSecret
				}
			}
			break
		}
	}
	return "", ""
}

// RunModalCommandWithEnv 执行带环境变量的 Modal 命令
func (a *App) RunModalCommandWithEnv(command string, args []string, workDir, tokenId, tokenSecret string) CommandResult {
	cmdStr := fmt.Sprintf("modal %s %s", command, strings.Join(args, " "))
	a.Log(LogTypeCommand, fmt.Sprintf("执行命令: %s", cmdStr))

	// 发送开始事件
	runtime.EventsEmit(a.ctx, "command:start", command)

	modalPath := a.getModalPath()
	cmd := exec.Command(modalPath, append([]string{command}, args...)...)
	if workDir != "" {
		// 将相对路径转换为绝对路径
		cmd.Dir = a.getProjectAbsolutePath(workDir)
	}

	// 设置环境变量
	env := os.Environ()
	if tokenId != "" && tokenSecret != "" {
		env = append(env, "MODAL_TOKEN_ID="+tokenId)
		env = append(env, "MODAL_TOKEN_SECRET="+tokenSecret)
		a.LogInfo(fmt.Sprintf("使用 Token ID: %s...", tokenId[:min(8, len(tokenId))]))
	}
	// 设置 UTF-8 编码，避免 Windows GBK 编码问题
	env = append(env, "PYTHONIOENCODING=utf-8")
	cmd.Env = env

	output, err := cmd.CombinedOutput()

	result := CommandResult{
		Success: err == nil,
		Output:  string(output),
	}

	if err != nil {
		result.Error = err.Error()
		a.LogError(fmt.Sprintf("命令执行失败: %s, 错误: %s, 输出: %s", cmdStr, err.Error(), string(output)))
	} else {
		a.LogInfo(fmt.Sprintf("命令执行成功: %s", cmdStr))
	}

	// 发送完成事件
	runtime.EventsEmit(a.ctx, "command:complete", result)

	return result
}

// RunModalCommandAsync 异步执行 Modal 命令，实时流式输出
func (a *App) RunModalCommandAsync(command string, args []string, workDir, tokenId, tokenSecret string) {
	cmdStr := fmt.Sprintf("modal %s %s", command, strings.Join(args, " "))
	a.Log(LogTypeCommand, fmt.Sprintf("执行命令: %s", cmdStr))

	// 发送开始事件
	runtime.EventsEmit(a.ctx, "command:start", command)

	go func() {
		modalPath := a.getModalPath()
		cmd := exec.Command(modalPath, append([]string{command}, args...)...)
		if workDir != "" {
			cmd.Dir = a.getProjectAbsolutePath(workDir)
		}

		// 设置环境变量
		env := os.Environ()
		if tokenId != "" && tokenSecret != "" {
			env = append(env, "MODAL_TOKEN_ID="+tokenId)
			env = append(env, "MODAL_TOKEN_SECRET="+tokenSecret)
			a.LogInfo(fmt.Sprintf("使用 Token ID: %s...", tokenId[:min(8, len(tokenId))]))
		}
		env = append(env, "PYTHONIOENCODING=utf-8")
		cmd.Env = env

		// 创建管道读取输出
		stdout, err := cmd.StdoutPipe()
		if err != nil {
			runtime.EventsEmit(a.ctx, "command:output", fmt.Sprintf("创建stdout管道失败: %v", err))
			runtime.EventsEmit(a.ctx, "command:complete", CommandResult{Success: false, Error: err.Error()})
			return
		}
		stderr, err := cmd.StderrPipe()
		if err != nil {
			runtime.EventsEmit(a.ctx, "command:output", fmt.Sprintf("创建stderr管道失败: %v", err))
			runtime.EventsEmit(a.ctx, "command:complete", CommandResult{Success: false, Error: err.Error()})
			return
		}

		// 启动命令
		if err := cmd.Start(); err != nil {
			runtime.EventsEmit(a.ctx, "command:output", fmt.Sprintf("启动命令失败: %v", err))
			runtime.EventsEmit(a.ctx, "command:complete", CommandResult{Success: false, Error: err.Error()})
			return
		}

		// 保存命令引用，用于支持中止操作
		a.cmdMutex.Lock()
		a.runningCmd = cmd
		a.cmdMutex.Unlock()

		// 合并 stdout 和 stderr，实时读取并发送
		merged := io.MultiReader(stdout, stderr)
		scanner := bufio.NewScanner(merged)

		// 增加 scanner 缓冲区大小，防止长行被截断
		buf := make([]byte, 0, 64*1024)
		scanner.Buffer(buf, 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			runtime.EventsEmit(a.ctx, "command:output", line)
		}

		// 等待命令完成
		err = cmd.Wait()

		// 清空命令引用
		a.cmdMutex.Lock()
		a.runningCmd = nil
		a.cmdMutex.Unlock()

		result := CommandResult{
			Success: err == nil,
			Output:  "",
		}
		if err != nil {
			result.Error = err.Error()
			a.LogError(fmt.Sprintf("命令执行失败: %s, 错误: %s", cmdStr, err.Error()))
		} else {
			a.LogInfo(fmt.Sprintf("命令执行成功: %s", cmdStr))
		}

		// 发送完成事件
		runtime.EventsEmit(a.ctx, "command:complete", result)
	}()
}

// CancelRunningCommand 取消正在运行的命令
func (a *App) CancelRunningCommand() bool {
	a.cmdMutex.Lock()
	defer a.cmdMutex.Unlock()

	if a.runningCmd != nil && a.runningCmd.Process != nil {
		a.LogWarning("用户取消命令执行")
		if err := a.runningCmd.Process.Kill(); err != nil {
			a.LogError(fmt.Sprintf("取消命令失败: %v", err))
			return false
		}
		runtime.EventsEmit(a.ctx, "command:output", "⚠️ 命令已被用户中止")
		return true
	}
	return false
}

// DeployScriptAsync 异步部署脚本
func (a *App) DeployScriptAsync(scriptPath string, workDir string) {
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)
	a.RunModalCommandAsync("deploy", []string{scriptPath}, workDir, tokenId, tokenSecret)
}

// modifyScriptForEnvironment 修改脚本中的应用名称和 Volume 名称，添加环境后缀
func (a *App) modifyScriptForEnvironment(content string, suffix string) string {
	if suffix == "" {
		return content
	}

	// 确保后缀以 - 开头
	if !strings.HasPrefix(suffix, "-") {
		suffix = "-" + suffix
	}

	// 匹配 modal.App(name="xxx") 或 modal.App("xxx") 格式
	// 支持: modal.App(name="app-name") 和 modal.App("app-name")
	appNamePattern := regexp.MustCompile(`(modal\.App\s*\(\s*(?:name\s*=\s*)?["'])([^"']+)(["'])`)
	content = appNamePattern.ReplaceAllStringFunc(content, func(match string) string {
		submatches := appNamePattern.FindStringSubmatch(match)
		if len(submatches) == 4 {
			appName := submatches[2]
			// 避免重复添加后缀
			if !strings.HasSuffix(appName, suffix) {
				return submatches[1] + appName + suffix + submatches[3]
			}
		}
		return match
	})

	// 匹配 modal.Volume.from_name("xxx") 格式
	volumePattern := regexp.MustCompile(`(modal\.Volume\.from_name\s*\(\s*["'])([^"']+)(["'])`)
	content = volumePattern.ReplaceAllStringFunc(content, func(match string) string {
		submatches := volumePattern.FindStringSubmatch(match)
		if len(submatches) == 4 {
			volumeName := submatches[2]
			// 避免重复添加后缀
			if !strings.HasSuffix(volumeName, suffix) {
				return submatches[1] + volumeName + suffix + submatches[3]
			}
		}
		return match
	})

	// 匹配 modal.Secret.from_name("xxx") 格式
	secretPattern := regexp.MustCompile(`(modal\.Secret\.from_name\s*\(\s*["'])([^"']+)(["'])`)
	content = secretPattern.ReplaceAllStringFunc(content, func(match string) string {
		submatches := secretPattern.FindStringSubmatch(match)
		if len(submatches) == 4 {
			secretName := submatches[2]
			// 避免重复添加后缀
			if !strings.HasSuffix(secretName, suffix) {
				return submatches[1] + secretName + suffix + submatches[3]
			}
		}
		return match
	})

	return content
}

// DeployScriptToAppAsync 异步部署脚本到指定的 Modal App 环境
func (a *App) DeployScriptToAppAsync(scriptPath string, workDir string, appId string) error {
	a.LogInfo(fmt.Sprintf("[DeployToApp] 部署脚本到环境: scriptPath=%s, appId=%s", scriptPath, appId))

	// 获取指定的 Modal App
	modalApp := a.GetModalAppByID(appId)
	if modalApp == nil {
		return fmt.Errorf("未找到 Modal App: %s", appId)
	}

	// 读取脚本内容
	workDirAbs := a.getProjectAbsolutePath(workDir)
	scriptFullPath := filepath.Join(workDirAbs, scriptPath)
	content, err := os.ReadFile(scriptFullPath)
	if err != nil {
		return fmt.Errorf("读取脚本失败: %v", err)
	}

	// 修改脚本中的应用名称
	modifiedContent := a.modifyScriptForEnvironment(string(content), modalApp.Suffix)

	// 创建临时文件
	tempFile := filepath.Join(workDirAbs, "_temp_"+filepath.Base(scriptPath))
	if err := os.WriteFile(tempFile, []byte(modifiedContent), 0644); err != nil {
		return fmt.Errorf("创建临时文件失败: %v", err)
	}

	a.LogInfo(fmt.Sprintf("[DeployToApp] 使用环境: name=%s, suffix=%s, tokenId=%s...",
		modalApp.Name, modalApp.Suffix, modalApp.TokenID[:min(8, len(modalApp.TokenID))]))

	// 使用指定环境的 Token 执行部署
	go func() {
		a.RunModalCommandAsync("deploy", []string{filepath.Base(tempFile)}, workDir, modalApp.TokenID, modalApp.TokenSecret)
		// 注意：临时文件会在下次部署时被覆盖
	}()

	return nil
}

// RunScriptToAppAsync 异步运行脚本到指定的 Modal App 环境
func (a *App) RunScriptToAppAsync(scriptPath string, workDir string, appId string) error {
	a.LogInfo(fmt.Sprintf("[RunToApp] 运行脚本到环境: scriptPath=%s, appId=%s", scriptPath, appId))

	// 获取指定的 Modal App
	modalApp := a.GetModalAppByID(appId)
	if modalApp == nil {
		return fmt.Errorf("未找到 Modal App: %s", appId)
	}

	// 读取脚本内容
	workDirAbs := a.getProjectAbsolutePath(workDir)
	scriptFullPath := filepath.Join(workDirAbs, scriptPath)
	content, err := os.ReadFile(scriptFullPath)
	if err != nil {
		return fmt.Errorf("读取脚本失败: %v", err)
	}

	// 修改脚本中的应用名称
	modifiedContent := a.modifyScriptForEnvironment(string(content), modalApp.Suffix)

	// 创建临时文件
	tempFile := filepath.Join(workDirAbs, "_temp_"+filepath.Base(scriptPath))
	if err := os.WriteFile(tempFile, []byte(modifiedContent), 0644); err != nil {
		return fmt.Errorf("创建临时文件失败: %v", err)
	}

	a.LogInfo(fmt.Sprintf("[RunToApp] 使用环境: name=%s, suffix=%s, tokenId=%s...",
		modalApp.Name, modalApp.Suffix, modalApp.TokenID[:min(8, len(modalApp.TokenID))]))

	// 使用指定环境的 Token 执行运行
	go func() {
		a.RunModalCommandAsync("run", []string{filepath.Base(tempFile)}, workDir, modalApp.TokenID, modalApp.TokenSecret)
	}()

	return nil
}

// RunScriptWithArgsAsync 异步运行脚本（带命令行参数）
func (a *App) RunScriptWithArgsAsync(scriptPath string, workDir string, argsString string) {
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)

	// 构建参数列表
	args := []string{scriptPath}
	if argsString != "" {
		// 解析参数字符串，支持 --key=value 格式
		argParts := strings.Fields(argsString)
		args = append(args, argParts...)
	}

	a.LogInfo(fmt.Sprintf("[RunWithArgs] 执行脚本: %s, 参数: %s", scriptPath, argsString))
	a.RunModalCommandAsync("run", args, workDir, tokenId, tokenSecret)
}

// DeployScriptWithContentAsync 异步部署带内容替换的脚本
func (a *App) DeployScriptWithContentAsync(scriptPath string, workDir string, content string) error {
	workDirAbs := a.getProjectAbsolutePath(workDir)
	// 注意：Modal 不允许文件名包含多个点号，所以使用下划线前缀
	tempFile := filepath.Join(workDirAbs, "_temp_"+filepath.Base(scriptPath))

	if err := os.WriteFile(tempFile, []byte(content), 0644); err != nil {
		return fmt.Errorf("创建临时文件失败: %v", err)
	}

	// 异步执行，完成后删除临时文件
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)

	go func() {
		a.RunModalCommandAsync("deploy", []string{filepath.Base(tempFile)}, workDir, tokenId, tokenSecret)
		// 注意：这里不能立即删除临时文件，因为命令是异步的
		// 临时文件会在下次部署时被覆盖，或者可以在 command:complete 事件后清理
	}()

	return nil
}

// RunScriptWithContentAsync 异步运行带内容替换的脚本（使用 modal run）
func (a *App) RunScriptWithContentAsync(scriptPath string, workDir string, content string) error {
	workDirAbs := a.getProjectAbsolutePath(workDir)
	// 注意：Modal 不允许文件名包含多个点号，所以使用下划线前缀
	tempFile := filepath.Join(workDirAbs, "_temp_"+filepath.Base(scriptPath))

	if err := os.WriteFile(tempFile, []byte(content), 0644); err != nil {
		return fmt.Errorf("创建临时文件失败: %v", err)
	}

	// 异步执行
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)

	go func() {
		a.RunModalCommandAsync("run", []string{filepath.Base(tempFile)}, workDir, tokenId, tokenSecret)
	}()

	return nil
}

// DeployScriptWithLogAsync 异步部署脚本并记录执行日志
func (a *App) DeployScriptWithLogAsync(scriptPath string, workDir string, content string, projectID string, projectName string, scriptName string, variables map[string]string) (string, error) {
	workDirAbs := a.getProjectAbsolutePath(workDir)
	tempFile := filepath.Join(workDirAbs, "_temp_"+filepath.Base(scriptPath))

	if err := os.WriteFile(tempFile, []byte(content), 0644); err != nil {
		return "", fmt.Errorf("创建临时文件失败: %v", err)
	}

	// 创建执行日志
	logID, err := a.CreateExecutionLog(projectID, projectName, scriptName, scriptPath, content, "deploy", variables)
	if err != nil {
		a.LogError(fmt.Sprintf("创建执行日志失败: %v", err))
	}

	// 异步执行
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)

	go func() {
		a.RunModalCommandAsyncWithLog("deploy", []string{filepath.Base(tempFile)}, workDir, tokenId, tokenSecret, logID)
	}()

	return logID, nil
}

// RunScriptWithLogAsync 异步运行脚本并记录执行日志
func (a *App) RunScriptWithLogAsync(scriptPath string, workDir string, content string, projectID string, projectName string, scriptName string, variables map[string]string) (string, error) {
	workDirAbs := a.getProjectAbsolutePath(workDir)
	tempFile := filepath.Join(workDirAbs, "_temp_"+filepath.Base(scriptPath))

	if err := os.WriteFile(tempFile, []byte(content), 0644); err != nil {
		return "", fmt.Errorf("创建临时文件失败: %v", err)
	}

	// 创建执行日志
	logID, err := a.CreateExecutionLog(projectID, projectName, scriptName, scriptPath, content, "run", variables)
	if err != nil {
		a.LogError(fmt.Sprintf("创建执行日志失败: %v", err))
	}

	// 异步执行
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)

	go func() {
		a.RunModalCommandAsyncWithLog("run", []string{filepath.Base(tempFile)}, workDir, tokenId, tokenSecret, logID)
	}()

	return logID, nil
}

// RunModalCommandAsyncWithLog 异步执行 Modal 命令并更新日志
func (a *App) RunModalCommandAsyncWithLog(command string, args []string, workDir, tokenId, tokenSecret, logID string) {
	cmdStr := fmt.Sprintf("modal %s %s", command, strings.Join(args, " "))
	a.Log(LogTypeCommand, fmt.Sprintf("执行命令: %s", cmdStr))

	// 发送开始事件
	runtime.EventsEmit(a.ctx, "command:start", command)

	go func() {
		var outputBuilder strings.Builder

		modalPath := a.getModalPath()
		cmd := exec.Command(modalPath, append([]string{command}, args...)...)
		if workDir != "" {
			cmd.Dir = a.getProjectAbsolutePath(workDir)
		}

		// 设置环境变量
		env := os.Environ()
		if tokenId != "" && tokenSecret != "" {
			env = append(env, "MODAL_TOKEN_ID="+tokenId)
			env = append(env, "MODAL_TOKEN_SECRET="+tokenSecret)
		}
		env = append(env, "PYTHONIOENCODING=utf-8")
		cmd.Env = env

		// 创建管道读取输出
		stdout, err := cmd.StdoutPipe()
		if err != nil {
			errMsg := fmt.Sprintf("创建stdout管道失败: %v", err)
			runtime.EventsEmit(a.ctx, "command:output", errMsg)
			runtime.EventsEmit(a.ctx, "command:complete", CommandResult{Success: false, Error: err.Error()})
			if logID != "" {
				a.UpdateExecutionLog(logID, "failed", errMsg)
			}
			return
		}
		stderr, err := cmd.StderrPipe()
		if err != nil {
			errMsg := fmt.Sprintf("创建stderr管道失败: %v", err)
			runtime.EventsEmit(a.ctx, "command:output", errMsg)
			runtime.EventsEmit(a.ctx, "command:complete", CommandResult{Success: false, Error: err.Error()})
			if logID != "" {
				a.UpdateExecutionLog(logID, "failed", errMsg)
			}
			return
		}

		// 启动命令
		if err := cmd.Start(); err != nil {
			errMsg := fmt.Sprintf("启动命令失败: %v", err)
			runtime.EventsEmit(a.ctx, "command:output", errMsg)
			runtime.EventsEmit(a.ctx, "command:complete", CommandResult{Success: false, Error: err.Error()})
			if logID != "" {
				a.UpdateExecutionLog(logID, "failed", errMsg)
			}
			return
		}

		// 保存命令引用
		a.cmdMutex.Lock()
		a.runningCmd = cmd
		a.cmdMutex.Unlock()

		// 合并 stdout 和 stderr，实时读取并发送
		merged := io.MultiReader(stdout, stderr)
		scanner := bufio.NewScanner(merged)
		buf := make([]byte, 0, 64*1024)
		scanner.Buffer(buf, 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			runtime.EventsEmit(a.ctx, "command:output", line)
			outputBuilder.WriteString(line + "\n")
		}

		// 等待命令完成
		err = cmd.Wait()

		// 清空命令引用
		a.cmdMutex.Lock()
		a.runningCmd = nil
		a.cmdMutex.Unlock()

		result := CommandResult{
			Success: err == nil,
			Output:  outputBuilder.String(),
		}

		status := "success"
		if err != nil {
			result.Error = err.Error()
			status = "failed"
			a.LogError(fmt.Sprintf("命令执行失败: %s, 错误: %s", cmdStr, err.Error()))
		} else {
			a.LogInfo(fmt.Sprintf("命令执行成功: %s", cmdStr))
		}

		// 更新执行日志
		if logID != "" {
			// 限制输出长度（保留最后 50KB）
			output := outputBuilder.String()
			if len(output) > 50*1024 {
				output = "...(输出过长，已截断)...\n" + output[len(output)-50*1024:]
			}
			a.UpdateExecutionLog(logID, status, output)
		}

		// 发送完成事件
		runtime.EventsEmit(a.ctx, "command:complete", result)
	}()
}

// RunScriptAsync 异步运行脚本（不替换内容）
func (a *App) RunScriptAsync(scriptPath string, workDir string) {
	tokenId, tokenSecret := a.getTokenForProjectPath(workDir)
	a.RunModalCommandAsync("run", []string{scriptPath}, workDir, tokenId, tokenSecret)
}

// StopApp 停止Modal应用
func (a *App) StopApp(appName string) CommandResult {
	return a.RunModalCommand("app", []string{"stop", appName}, "")
}

// GetModalApps 获取Modal应用列表
func (a *App) GetModalApps() CommandResult {
	return a.RunModalCommand("app", []string{"list"}, "")
}

// SelectDirectory 选择目录
func (a *App) SelectDirectory() (string, error) {
	return runtime.OpenDirectoryDialog(a.ctx, runtime.OpenDialogOptions{
		Title: "选择项目目录",
	})
}

// CheckModalInstalled 检查Modal是否安装
func (a *App) CheckModalInstalled() bool {
	modalPath := a.getModalPath()
	cmd := exec.Command(modalPath, "--version")
	err := cmd.Run()
	return err == nil
}

// ========== Modal App 管理 ==========

// GetModalAppList 获取所有Modal应用配置
func (a *App) GetModalAppList() []ModalApp {
	apps := []ModalApp{}
	configPath := filepath.Join(a.projectsDir, "modal_apps.json")

	data, err := os.ReadFile(configPath)
	if err != nil {
		return apps
	}

	json.Unmarshal(data, &apps)
	return apps
}

// SaveModalAppList 保存Modal应用列表
func (a *App) SaveModalAppList(apps []ModalApp) error {
	configPath := filepath.Join(a.projectsDir, "modal_apps.json")
	data, err := json.MarshalIndent(apps, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(configPath, data, 0644)
}

// CreateModalApp 创建新的Modal应用配置
func (a *App) CreateModalApp(name, appName, description, token, tokenId, tokenSecret, workspace, suffix string) (*ModalApp, error) {
	a.LogInfo(fmt.Sprintf("[ModalApp] 开始创建应用配置: name=%s, appName=%s, workspace=%s, suffix=%s", name, appName, workspace, suffix))

	apps := a.GetModalAppList()

	app := ModalApp{
		ID:          fmt.Sprintf("%d", time.Now().UnixNano()),
		Name:        name,
		AppName:     appName,
		Description: description,
		Token:       token,
		TokenID:     tokenId,
		TokenSecret: tokenSecret,
		Workspace:   workspace,
		Suffix:      suffix,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	apps = append(apps, app)
	if err := a.SaveModalAppList(apps); err != nil {
		a.LogError(fmt.Sprintf("[ModalApp] 保存应用配置失败: %v", err))
		return nil, err
	}

	a.LogInfo(fmt.Sprintf("[ModalApp] 应用配置创建成功: id=%s, name=%s", app.ID, name))
	return &app, nil
}

// UpdateModalApp 更新Modal应用配置
func (a *App) UpdateModalApp(id, name, appName, description, token, tokenId, tokenSecret, workspace, suffix string) error {
	a.LogInfo(fmt.Sprintf("[ModalApp] 开始更新应用配置: id=%s, name=%s, suffix=%s", id, name, suffix))

	apps := a.GetModalAppList()
	found := false

	for i, app := range apps {
		if app.ID == id {
			apps[i].Name = name
			apps[i].AppName = appName
			apps[i].Description = description
			apps[i].Token = token
			apps[i].TokenID = tokenId
			apps[i].TokenSecret = tokenSecret
			apps[i].Workspace = workspace
			apps[i].Suffix = suffix
			apps[i].UpdatedAt = time.Now()
			found = true
			break
		}
	}

	if !found {
		a.LogError(fmt.Sprintf("[ModalApp] 更新失败: 应用不存在, id=%s", id))
		return fmt.Errorf("应用配置不存在")
	}

	if err := a.SaveModalAppList(apps); err != nil {
		a.LogError(fmt.Sprintf("[ModalApp] 保存应用配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[ModalApp] 应用配置更新成功: id=%s, name=%s", id, name))
	return nil
}

// DeleteModalApp 删除Modal应用配置
func (a *App) DeleteModalApp(id string) error {
	a.LogInfo(fmt.Sprintf("[ModalApp] 开始删除应用配置: id=%s", id))

	apps := a.GetModalAppList()
	newApps := []ModalApp{}
	var deletedApp *ModalApp

	for _, app := range apps {
		if app.ID != id {
			newApps = append(newApps, app)
		} else {
			deletedApp = &app
		}
	}

	if deletedApp != nil {
		a.LogInfo(fmt.Sprintf("[ModalApp] 找到应用: name=%s", deletedApp.Name))
	} else {
		a.LogWarning(fmt.Sprintf("[ModalApp] 应用不存在: id=%s", id))
	}

	if err := a.SaveModalAppList(newApps); err != nil {
		a.LogError(fmt.Sprintf("[ModalApp] 保存应用配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[ModalApp] 应用配置删除成功: id=%s", id))
	return nil
}

// GetModalAppByID 根据ID获取Modal应用
func (a *App) GetModalAppByID(id string) *ModalApp {
	apps := a.GetModalAppList()
	for _, app := range apps {
		if app.ID == id {
			return &app
		}
	}
	return nil
}

// TestModalConnection 测试Modal连接
func (a *App) TestModalConnection(token, workspace string) CommandResult {
	modalPath := a.getModalPath()

	// 先检查 modal 是否存在
	if _, err := os.Stat(modalPath); os.IsNotExist(err) && modalPath == "modal" {
		// 尝试用 where 命令查找
		whereCmd := exec.Command("where", "modal")
		if whereOutput, err := whereCmd.Output(); err == nil && len(whereOutput) > 0 {
			modalPath = strings.TrimSpace(strings.Split(string(whereOutput), "\n")[0])
		} else {
			return CommandResult{
				Success: false,
				Output:  "",
				Error:   "未找到 Modal CLI。请先安装: pip install modal",
			}
		}
	}

	// 构建环境变量
	env := os.Environ()
	if token != "" {
		parts := strings.Split(token, ":")
		env = append(env, "MODAL_TOKEN_ID="+parts[0])
		if len(parts) > 1 {
			env = append(env, "MODAL_TOKEN_SECRET="+parts[1])
		}
	}

	// 执行 modal --version 来测试基本安装
	cmd := exec.Command(modalPath, "--version")
	cmd.Env = env

	output, err := cmd.CombinedOutput()

	if err != nil {
		return CommandResult{
			Success: false,
			Output:  string(output),
			Error:   fmt.Sprintf("Modal CLI 执行失败: %s", err.Error()),
		}
	}

	// 如果版本检查通过，再测试 token（如果提供了的话）
	result := CommandResult{
		Success: true,
		Output:  fmt.Sprintf("Modal CLI: %s", strings.TrimSpace(string(output))),
	}

	return result
}

// ========== Modal 服务器操作命令 ==========

// RunModalCommandWithToken 执行带 Token 的 Modal 命令
func (a *App) RunModalCommandWithToken(command string, args []string, token string) CommandResult {
	return a.RunModalCommandWithTokenPair(command, args, "", "", token)
}

// RunModalCommandWithTokenPair 执行带 TokenID 和 TokenSecret 的 Modal 命令
func (a *App) RunModalCommandWithTokenPair(command string, args []string, tokenId, tokenSecret, token string) CommandResult {
	modalPath := a.getModalPath()
	cmd := exec.Command(modalPath, append([]string{command}, args...)...)

	// 设置环境变量
	env := os.Environ()

	// 优先使用 tokenId 和 tokenSecret
	if tokenId != "" && tokenSecret != "" {
		env = append(env, "MODAL_TOKEN_ID="+tokenId)
		env = append(env, "MODAL_TOKEN_SECRET="+tokenSecret)
	} else if token != "" {
		// 兼容旧格式 token_id:token_secret
		parts := strings.Split(token, ":")
		if len(parts) >= 1 {
			env = append(env, "MODAL_TOKEN_ID="+parts[0])
		}
		if len(parts) >= 2 {
			env = append(env, "MODAL_TOKEN_SECRET="+parts[1])
		}
	}
	// 设置 UTF-8 编码，避免 Windows GBK 编码问题
	env = append(env, "PYTHONIOENCODING=utf-8")
	cmd.Env = env

	output, err := cmd.CombinedOutput()

	result := CommandResult{
		Success: err == nil,
		Output:  string(output),
	}

	if err != nil {
		result.Error = err.Error()
	}

	return result
}

// ModalAppListWithToken 获取 Modal 平台上的应用列表
func (a *App) ModalAppListWithToken(token string) CommandResult {
	return a.RunModalCommandWithToken("app", []string{"list"}, token)
}

// ModalAppStopWithToken 停止指定应用
func (a *App) ModalAppStopWithToken(appName, token string) CommandResult {
	return a.RunModalCommandWithToken("app", []string{"stop", appName}, token)
}

// ModalAppLogsWithToken 获取应用日志
func (a *App) ModalAppLogsWithToken(appName, token string) CommandResult {
	return a.RunModalCommandWithToken("app", []string{"logs", appName}, token)
}

// ModalVolumeListWithToken 获取 Volume 列表
func (a *App) ModalVolumeListWithToken(token string) CommandResult {
	return a.RunModalCommandWithToken("volume", []string{"list"}, token)
}

// ModalSecretListWithToken 获取 Secret 列表
func (a *App) ModalSecretListWithToken(token string) CommandResult {
	return a.RunModalCommandWithToken("secret", []string{"list"}, token)
}

// ModalContainerListWithToken 获取运行中的容器列表
func (a *App) ModalContainerListWithToken(token string) CommandResult {
	return a.RunModalCommandWithToken("container", []string{"list"}, token)
}

// ========== 带 TokenPair 的服务器操作 ==========

// ModalAppListWithTokenPair 获取 Modal 平台上的应用列表
func (a *App) ModalAppListWithTokenPair(tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("app", []string{"list"}, tokenId, tokenSecret, "")
}

// ModalAppStopWithTokenPair 停止指定应用
func (a *App) ModalAppStopWithTokenPair(appName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("app", []string{"stop", appName}, tokenId, tokenSecret, "")
}

// ModalAppLogsWithTokenPair 获取应用日志
func (a *App) ModalAppLogsWithTokenPair(appName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("app", []string{"logs", appName}, tokenId, tokenSecret, "")
}

// ModalVolumeListWithTokenPair 获取 Volume 列表
func (a *App) ModalVolumeListWithTokenPair(tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("volume", []string{"list"}, tokenId, tokenSecret, "")
}

// ModalSecretListWithTokenPair 获取 Secret 列表
func (a *App) ModalSecretListWithTokenPair(tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("secret", []string{"list"}, tokenId, tokenSecret, "")
}

// ModalContainerListWithTokenPair 获取运行中的容器列表
func (a *App) ModalContainerListWithTokenPair(tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("container", []string{"list"}, tokenId, tokenSecret, "")
}

// ModalAppDescribeWithTokenPair 获取应用详细信息
func (a *App) ModalAppDescribeWithTokenPair(appName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("app", []string{"describe", appName, "--json"}, tokenId, tokenSecret, "")
}

// ModalAppStatsWithTokenPair 获取应用统计信息
func (a *App) ModalAppStatsWithTokenPair(appName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("app", []string{"stats", appName}, tokenId, tokenSecret, "")
}

// ModalVolumeGetWithTokenPair 获取特定 Volume 详情
func (a *App) ModalVolumeGetWithTokenPair(volumeName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("volume", []string{"get", volumeName}, tokenId, tokenSecret, "")
}

// ModalAppHistoryWithTokenPair 获取应用执行历史
func (a *App) ModalAppHistoryWithTokenPair(appName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("app", []string{"history", appName}, tokenId, tokenSecret, "")
}

// ModalAppDeleteWithTokenPair 删除应用
func (a *App) ModalAppDeleteWithTokenPair(appName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("app", []string{"delete", appName, "--yes"}, tokenId, tokenSecret, "")
}

// ModalVolumeLsWithTokenPair 列出 Volume 内文件
func (a *App) ModalVolumeLsWithTokenPair(volumeName, path, tokenId, tokenSecret string) CommandResult {
	if path == "" {
		path = "/"
	}
	return a.RunModalCommandWithTokenPair("volume", []string{"ls", volumeName, path}, tokenId, tokenSecret, "")
}

// ModalVolumeDeleteWithTokenPair 删除 Volume
func (a *App) ModalVolumeDeleteWithTokenPair(volumeName, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("volume", []string{"delete", volumeName, "--yes"}, tokenId, tokenSecret, "")
}

// ModalVolumeRmWithTokenPair 删除 Volume 中的文件
func (a *App) ModalVolumeRmWithTokenPair(volumeName, filePath, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("volume", []string{"rm", volumeName, filePath}, tokenId, tokenSecret, "")
}

// ModalContainerStopWithTokenPair 停止容器
func (a *App) ModalContainerStopWithTokenPair(containerId, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("container", []string{"stop", containerId}, tokenId, tokenSecret, "")
}

// ModalContainerExecWithTokenPair 在容器中执行命令
func (a *App) ModalContainerExecWithTokenPair(containerId, command, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("container", []string{"exec", containerId, command}, tokenId, tokenSecret, "")
}

// ModalProfileWithTokenPair 获取当前配置信息
func (a *App) ModalProfileWithTokenPair(tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("profile", []string{"current"}, tokenId, tokenSecret, "")
}

// ModalEnvironmentListWithTokenPair 获取环境列表
func (a *App) ModalEnvironmentListWithTokenPair(tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("environment", []string{"list"}, tokenId, tokenSecret, "")
}

// ModalNfsListWithTokenPair 获取 NFS 列表
func (a *App) ModalNfsListWithTokenPair(tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("nfs", []string{"list"}, tokenId, tokenSecret, "")
}

// ModalVolumePutWithTokenPair 上传本地文件到 Volume
func (a *App) ModalVolumePutWithTokenPair(volumeName, localPath, remotePath, tokenId, tokenSecret string) CommandResult {
	return a.RunModalCommandWithTokenPair("volume", []string{"put", volumeName, localPath, remotePath}, tokenId, tokenSecret, "")
}

// ModalVolumePutAsyncWithTokenPair 异步上传本地文件到 Volume (支持大文件)
func (a *App) ModalVolumePutAsyncWithTokenPair(volumeName, localPath, remotePath, tokenId, tokenSecret string) CommandResult {
	modalPath := a.getModalPath()

	// 构建环境变量
	env := os.Environ()
	if tokenId != "" && tokenSecret != "" {
		env = append(env, "MODAL_TOKEN_ID="+tokenId)
		env = append(env, "MODAL_TOKEN_SECRET="+tokenSecret)
	}

	// 执行 modal volume put
	args := []string{"volume", "put", volumeName, localPath, remotePath}
	cmd := exec.Command(modalPath, args...)
	cmd.Env = env

	output, err := cmd.CombinedOutput()
	if err != nil {
		return CommandResult{
			Success: false,
			Output:  string(output),
			Error:   err.Error(),
		}
	}

	return CommandResult{
		Success: true,
		Output:  string(output),
	}
}

// 保留无 Token 版本用于兼容
func (a *App) ModalAppList() CommandResult {
	return a.RunModalCommandWithToken("app", []string{"list"}, "")
}

func (a *App) ModalAppStop(appName string) CommandResult {
	return a.RunModalCommandWithToken("app", []string{"stop", appName}, "")
}

func (a *App) ModalAppLogs(appName string) CommandResult {
	return a.RunModalCommandWithToken("app", []string{"logs", appName}, "")
}

func (a *App) ModalVolumeList() CommandResult {
	return a.RunModalCommandWithToken("volume", []string{"list"}, "")
}

func (a *App) ModalSecretList() CommandResult {
	return a.RunModalCommandWithToken("secret", []string{"list"}, "")
}

func (a *App) ModalContainerList() CommandResult {
	return a.RunModalCommandWithToken("container", []string{"list"}, "")
}

// ModalTokenNew 打开浏览器进行 Modal 登录
func (a *App) ModalTokenNew() CommandResult {
	modalPath := a.getModalPath()

	// 执行 modal token new，这会打开浏览器
	cmd := exec.Command(modalPath, "token", "new")
	output, err := cmd.CombinedOutput()

	result := CommandResult{
		Success: err == nil,
		Output:  string(output),
	}

	if err != nil {
		result.Error = err.Error()
	}

	return result
}

// ModalTokenSet 设置 Token
func (a *App) ModalTokenSet(tokenId, tokenSecret string) CommandResult {
	modalPath := a.getModalPath()

	cmd := exec.Command(modalPath, "token", "set", "--token-id", tokenId, "--token-secret", tokenSecret)
	output, err := cmd.CombinedOutput()

	result := CommandResult{
		Success: err == nil,
		Output:  string(output),
	}

	if err != nil {
		result.Error = err.Error()
	}

	return result
}

// ========== 脚本管理 API ==========

// CreateScript 创建新脚本
func (a *App) CreateScript(projectID, name, fileName, description, template string) error {
	a.LogInfo(fmt.Sprintf("[CreateScript] 开始创建脚本: projectId=%s, name=%s, fileName=%s", projectID, name, fileName))

	projects := a.GetProjects()

	// 找到对应的项目
	projectIndex := -1
	var project *Project
	for i := range projects {
		if projects[i].ID == projectID {
			projectIndex = i
			project = &projects[i]
			break
		}
	}

	if project == nil {
		a.LogError(fmt.Sprintf("[CreateScript] 创建失败: 项目不存在, projectId=%s", projectID))
		return fmt.Errorf("项目不存在")
	}

	a.LogInfo(fmt.Sprintf("[CreateScript] 找到项目: name=%s, path=%s", project.Name, project.Path))

	// 验证文件名
	if !strings.HasSuffix(fileName, ".py") {
		fileName = fileName + ".py"
	}

	// 计算项目绝对路径
	projectAbsPath := a.getProjectAbsolutePath(project.Path)
	a.LogInfo(fmt.Sprintf("[CreateScript] 项目绝对路径: %s", projectAbsPath))

	// 创建脚本文件（使用绝对路径）
	scriptAbsPath := filepath.Join(projectAbsPath, fileName)

	// 检查文件是否已存在
	if _, err := os.Stat(scriptAbsPath); err == nil {
		a.LogError(fmt.Sprintf("[CreateScript] 创建失败: 文件已存在, path=%s", scriptAbsPath))
		return fmt.Errorf("文件已存在: %s", fileName)
	}

	// 生成脚本内容
	content := a.generateScriptContent(name, description, template, project.Name)
	a.LogInfo(fmt.Sprintf("[CreateScript] 生成脚本内容, 长度=%d字节", len(content)))

	// 写入文件
	if err := os.WriteFile(scriptAbsPath, []byte(content), 0644); err != nil {
		a.LogError(fmt.Sprintf("[CreateScript] 写入文件失败: path=%s, error=%v", scriptAbsPath, err))
		return fmt.Errorf("创建文件失败: %v", err)
	}

	a.LogInfo(fmt.Sprintf("[CreateScript] 文件写入成功: %s", scriptAbsPath))

	// 更新项目配置（只存储相对路径）
	newScript := Script{
		Name:        name,
		Path:        fileName,
		FullPath:    "", // 不再存储绝对路径，运行时动态计算
		Description: description,
		Order:       len(project.Scripts),
	}

	projects[projectIndex].Scripts = append(projects[projectIndex].Scripts, newScript)
	projects[projectIndex].UpdatedAt = time.Now()

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[CreateScript] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[CreateScript] 脚本创建成功: %s/%s", project.Name, fileName))
	return nil
}

// RegisterExistingScript 注册已存在的脚本文件到项目配置
func (a *App) RegisterExistingScript(projectID, fileName, name, description string) error {
	a.LogInfo(fmt.Sprintf("[RegisterScript] 注册现有脚本: projectId=%s, fileName=%s", projectID, fileName))

	projects := a.GetProjects()

	// 找到对应的项目
	projectIndex := -1
	var project *Project
	for i := range projects {
		if projects[i].ID == projectID {
			projectIndex = i
			project = &projects[i]
			break
		}
	}

	if project == nil {
		a.LogError(fmt.Sprintf("[RegisterScript] 注册失败: 项目不存在, projectId=%s", projectID))
		return fmt.Errorf("项目不存在")
	}

	// 计算项目绝对路径
	projectAbsPath := a.getProjectAbsolutePath(project.Path)
	scriptAbsPath := filepath.Join(projectAbsPath, fileName)

	// 检查文件是否存在
	if _, err := os.Stat(scriptAbsPath); os.IsNotExist(err) {
		a.LogError(fmt.Sprintf("[RegisterScript] 注册失败: 文件不存在, path=%s", scriptAbsPath))
		return fmt.Errorf("文件不存在: %s", fileName)
	}

	// 检查是否已经注册
	for _, script := range project.Scripts {
		if script.Path == fileName {
			a.LogInfo(fmt.Sprintf("[RegisterScript] 脚本已存在于列表中: %s", fileName))
			return nil // 已存在，不需要重复注册
		}
	}

	// 如果没有提供名称，使用文件名
	if name == "" {
		name = strings.TrimSuffix(fileName, ".py")
	}

	// 添加到项目配置
	newScript := Script{
		Name:        name,
		Path:        fileName,
		FullPath:    "", // 运行时动态计算
		Description: description,
		Order:       len(project.Scripts),
	}

	projects[projectIndex].Scripts = append(projects[projectIndex].Scripts, newScript)
	projects[projectIndex].UpdatedAt = time.Now()

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[RegisterScript] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[RegisterScript] 脚本注册成功: %s/%s", project.Name, fileName))
	return nil
}

// generateScriptContent 生成脚本内容
func (a *App) generateScriptContent(name, description, template, appName string) string {
	// 如果 template 是完整的脚本内容（包含 import 或以 """ 开头），直接使用
	if strings.Contains(template, "import modal") || strings.HasPrefix(template, `"""`) || strings.HasPrefix(template, "#!/") {
		return template
	}

	if template == "" || template == "blank" {
		return fmt.Sprintf(`#!/usr/bin/env python3
"""
脚本名称: %s
描述: %s
"""

import modal

app = modal.App(name="%s")

# 在这里添加你的代码

if __name__ == "__main__":
    print("运行脚本: %s")
`, name, description, appName, name)
	}

	if template == "deploy" {
		return fmt.Sprintf(`#!/usr/bin/env python3
"""
%s
使用方法: modal deploy <filename>
"""

import modal

# 构建镜像
image = modal.Image.debian_slim(python_version="3.11")

# 创建应用
app = modal.App(name="%s", image=image)

@app.function()
def hello():
    print("Hello from Modal!")
    return {"status": "success", "message": "部署成功"}

if __name__ == "__main__":
    print("使用 modal deploy 命令部署此脚本")
`, description, appName)
	}

	if template == "run" {
		return fmt.Sprintf(`#!/usr/bin/env python3
"""
%s
使用方法: modal run <filename>
"""

import modal

app = modal.App(name="%s")

@app.function()
def run_task():
    print("执行任务...")
    # 在这里添加你的任务逻辑
    return {"status": "success"}

@app.local_entrypoint()
def main():
    print("开始执行...")
    result = run_task.remote()
    print(f"结果: {result}")
`, description, appName)
	}

	// 默认空白模板
	return fmt.Sprintf(`#!/usr/bin/env python3
"""
%s
"""

import modal

app = modal.App(name="%s")

# 添加你的代码

`, description, appName)
}

// DeleteScript 删除脚本
func (a *App) DeleteScript(projectID, scriptPath string, deleteFile bool) error {
	a.LogInfo(fmt.Sprintf("[DeleteScript] 开始删除脚本: projectId=%s, scriptPath=%s, deleteFile=%v", projectID, scriptPath, deleteFile))

	projects := a.GetProjects()

	// 找到对应的项目
	projectIndex := -1
	var project *Project
	for i := range projects {
		if projects[i].ID == projectID {
			projectIndex = i
			project = &projects[i]
			break
		}
	}

	if project == nil {
		a.LogError(fmt.Sprintf("[DeleteScript] 删除失败: 项目不存在, projectId=%s", projectID))
		return fmt.Errorf("项目不存在")
	}

	// 从 scripts 数组中删除
	newScripts := []Script{}
	var deletedScript *Script
	for _, script := range project.Scripts {
		if script.Path != scriptPath {
			newScripts = append(newScripts, script)
		} else {
			deletedScript = &script
		}
	}

	if deletedScript == nil {
		a.LogError(fmt.Sprintf("[DeleteScript] 删除失败: 脚本不存在, scriptPath=%s", scriptPath))
		return fmt.Errorf("脚本不存在")
	}

	// 如果需要，删除实际文件
	if deleteFile {
		// 使用辅助函数计算绝对路径
		fullPath := a.getScriptAbsolutePath(project.Path, scriptPath)
		a.LogInfo(fmt.Sprintf("[DeleteScript] 删除文件: %s", fullPath))
		if err := os.Remove(fullPath); err != nil && !os.IsNotExist(err) {
			a.LogError(fmt.Sprintf("[DeleteScript] 删除文件失败: path=%s, error=%v", fullPath, err))
			return fmt.Errorf("删除文件失败: %v", err)
		}
	}

	// 更新项目配置
	projects[projectIndex].Scripts = newScripts
	projects[projectIndex].UpdatedAt = time.Now()

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[DeleteScript] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[DeleteScript] 脚本删除成功: %s/%s", project.Name, scriptPath))
	return nil
}

// ReorderScripts 重新排序脚本
func (a *App) ReorderScripts(projectID string, scriptPaths []string) error {
	a.LogInfo(fmt.Sprintf("[ReorderScripts] 开始重排序脚本: projectId=%s, count=%d", projectID, len(scriptPaths)))

	projects := a.GetProjects()

	// 找到对应的项目
	projectIndex := -1
	var project *Project
	for i := range projects {
		if projects[i].ID == projectID {
			projectIndex = i
			project = &projects[i]
			break
		}
	}

	if project == nil {
		a.LogError(fmt.Sprintf("[ReorderScripts] 重排序失败: 项目不存在, projectId=%s", projectID))
		return fmt.Errorf("项目不存在")
	}

	// 创建路径到脚本的映射
	scriptMap := make(map[string]Script)
	for _, script := range project.Scripts {
		scriptMap[script.Path] = script
	}

	// 按新顺序重建脚本数组
	newScripts := []Script{}
	for i, path := range scriptPaths {
		if script, exists := scriptMap[path]; exists {
			script.Order = i
			newScripts = append(newScripts, script)
		}
	}

	// 更新项目配置
	projects[projectIndex].Scripts = newScripts
	projects[projectIndex].UpdatedAt = time.Now()

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[ReorderScripts] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[ReorderScripts] 脚本重排序成功: %s", project.Name))
	return nil
}

// MoveScript 移动脚本（上移或下移）
func (a *App) MoveScript(projectID, scriptPath string, direction string) error {
	a.LogInfo(fmt.Sprintf("[MoveScript] 开始移动脚本: projectId=%s, scriptPath=%s, direction=%s", projectID, scriptPath, direction))

	projects := a.GetProjects()

	// 找到对应的项目
	projectIndex := -1
	var project *Project
	for i := range projects {
		if projects[i].ID == projectID {
			projectIndex = i
			project = &projects[i]
			break
		}
	}

	if project == nil {
		a.LogError(fmt.Sprintf("[MoveScript] 移动失败: 项目不存在, projectId=%s", projectID))
		return fmt.Errorf("项目不存在")
	}

	// 找到脚本的当前索引
	currentIndex := -1
	for i, script := range project.Scripts {
		if script.Path == scriptPath {
			currentIndex = i
			break
		}
	}

	if currentIndex == -1 {
		a.LogError(fmt.Sprintf("[MoveScript] 移动失败: 脚本不存在, scriptPath=%s", scriptPath))
		return fmt.Errorf("脚本不存在")
	}

	// 计算新位置
	newIndex := currentIndex
	if direction == "up" && currentIndex > 0 {
		newIndex = currentIndex - 1
	} else if direction == "down" && currentIndex < len(project.Scripts)-1 {
		newIndex = currentIndex + 1
	} else {
		a.LogInfo("[MoveScript] 脚本已在边界，无需移动")
		return nil // 已经在边界，无需移动
	}

	// 交换位置
	scripts := project.Scripts
	scripts[currentIndex], scripts[newIndex] = scripts[newIndex], scripts[currentIndex]

	// 更新 Order 字段
	for i := range scripts {
		scripts[i].Order = i
	}

	// 更新项目配置
	projects[projectIndex].Scripts = scripts
	projects[projectIndex].UpdatedAt = time.Now()

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[MoveScript] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[MoveScript] 脚本移动成功: %s %s", scriptPath, direction))
	return nil
}

// UpdateScript 更新脚本元数据
func (a *App) UpdateScript(projectID, scriptPath, name, description string) error {
	a.LogInfo(fmt.Sprintf("[UpdateScript] 开始更新脚本: projectId=%s, scriptPath=%s, name=%s", projectID, scriptPath, name))

	projects := a.GetProjects()

	// 找到对应的项目
	projectIndex := -1
	var project *Project
	for i := range projects {
		if projects[i].ID == projectID {
			projectIndex = i
			project = &projects[i]
			break
		}
	}

	if project == nil {
		a.LogError(fmt.Sprintf("[UpdateScript] 更新失败: 项目不存在, projectId=%s", projectID))
		return fmt.Errorf("项目不存在")
	}

	// 找到并更新脚本
	found := false
	for i, script := range project.Scripts {
		if script.Path == scriptPath {
			projects[projectIndex].Scripts[i].Name = name
			projects[projectIndex].Scripts[i].Description = description
			found = true
			break
		}
	}

	if !found {
		a.LogError(fmt.Sprintf("[UpdateScript] 更新失败: 脚本不存在, scriptPath=%s", scriptPath))
		return fmt.Errorf("脚本不存在")
	}

	// 更新项目配置
	projects[projectIndex].UpdatedAt = time.Now()

	if err := a.SaveProjects(projects); err != nil {
		a.LogError(fmt.Sprintf("[UpdateScript] 保存项目配置失败: %v", err))
		return err
	}

	a.LogInfo(fmt.Sprintf("[UpdateScript] 脚本更新成功: %s/%s", project.Name, scriptPath))
	return nil
}

// ReadScriptContent 读取脚本文件内容
func (a *App) ReadScriptContent(scriptFullPath string) (string, error) {
	a.LogInfo(fmt.Sprintf("[FileIO] 读取脚本文件: %s", scriptFullPath))

	// 读取文件内容
	content, err := os.ReadFile(scriptFullPath)
	if err != nil {
		a.LogError(fmt.Sprintf("[FileIO] 读取脚本文件失败: path=%s, error=%v", scriptFullPath, err))
		return "", fmt.Errorf("读取脚本文件失败: %v", err)
	}

	a.LogInfo(fmt.Sprintf("[FileIO] 读取成功: path=%s, size=%d字节", scriptFullPath, len(content)))
	return string(content), nil
}

// SaveScriptContent 保存脚本内容到文件（覆盖）
func (a *App) SaveScriptContent(scriptFullPath, content string) error {
	a.LogInfo(fmt.Sprintf("[FileIO] 保存脚本文件: path=%s, size=%d字节", scriptFullPath, len(content)))

	// 写入文件，覆盖原有内容
	err := os.WriteFile(scriptFullPath, []byte(content), 0644)
	if err != nil {
		a.LogError(fmt.Sprintf("[FileIO] 保存脚本文件失败: path=%s, error=%v", scriptFullPath, err))
		return fmt.Errorf("保存脚本文件失败: %v", err)
	}

	a.LogInfo(fmt.Sprintf("[FileIO] 保存成功: %s", scriptFullPath))
	return nil
}

// FormatPythonCode 使用Black格式化Python代码
func (a *App) FormatPythonCode(code string) (string, error) {
	// 尝试使用black格式化代码
	// 方法1: 直接使用 black 命令
	cmd := exec.Command("black", "--quiet", "-")
	cmd.Stdin = strings.NewReader(code)

	output, err := cmd.CombinedOutput()
	if err == nil {
		return string(output), nil
	}

	// 方法2: 尝试使用 python -m black
	cmd = exec.Command("python", "-m", "black", "--quiet", "-")
	cmd.Stdin = strings.NewReader(code)

	output, err = cmd.CombinedOutput()
	if err == nil {
		return string(output), nil
	}

	// 方法3: 尝试使用 python3 -m black
	cmd = exec.Command("python3", "-m", "black", "--quiet", "-")
	cmd.Stdin = strings.NewReader(code)

	output, err = cmd.CombinedOutput()
	if err == nil {
		return string(output), nil
	}

	// 如果都失败了，返回友好的错误信息
	return "", fmt.Errorf("未安装Black格式化工具。请运行: pip install black")
}

// ========== IDE 集成功能 ==========

// IDEConfig IDE配置
type IDEConfig struct {
	Name     string `json:"name"`     // VSCode, Cursor, Windsurf等
	Path     string `json:"path"`     // IDE可执行文件路径
	Command  string `json:"command"`  // 命令行命令
	Icon     string `json:"icon"`     // 图标名称
	Enabled  bool   `json:"enabled"`  // 是否启用
	Detected bool   `json:"detected"` // 是否自动检测到
}

// DetectInstalledIDEs 自动检测系统已安装的IDE
func (a *App) DetectInstalledIDEs() []IDEConfig {
	ides := []IDEConfig{}

	// VSCode
	if vscodePath := a.detectVSCode(); vscodePath != "" {
		ides = append(ides, IDEConfig{
			Name:     "Visual Studio Code",
			Path:     vscodePath,
			Command:  "code",
			Icon:     "vscode",
			Enabled:  true,
			Detected: true,
		})
	}

	// Cursor
	if cursorPath := a.detectCursor(); cursorPath != "" {
		ides = append(ides, IDEConfig{
			Name:     "Cursor",
			Path:     cursorPath,
			Command:  "cursor",
			Icon:     "cursor",
			Enabled:  true,
			Detected: true,
		})
	}

	// Windsurf
	if windsurfPath := a.detectWindsurf(); windsurfPath != "" {
		ides = append(ides, IDEConfig{
			Name:     "Windsurf",
			Path:     windsurfPath,
			Command:  "windsurf",
			Icon:     "windsurf",
			Enabled:  true,
			Detected: true,
		})
	}

	// PyCharm
	if pycharmPath := a.detectPyCharm(); pycharmPath != "" {
		ides = append(ides, IDEConfig{
			Name:     "PyCharm",
			Path:     pycharmPath,
			Command:  "pycharm",
			Icon:     "pycharm",
			Enabled:  true,
			Detected: true,
		})
	}

	// Sublime Text
	if sublimePath := a.detectSublimeText(); sublimePath != "" {
		ides = append(ides, IDEConfig{
			Name:     "Sublime Text",
			Path:     sublimePath,
			Command:  "subl",
			Icon:     "sublime",
			Enabled:  true,
			Detected: true,
		})
	}

	return ides
}

// detectVSCode 检测VSCode
func (a *App) detectVSCode() string {
	// 尝试从PATH找到code命令
	if path, err := exec.LookPath("code"); err == nil {
		return path
	}

	// Windows常见路径
	homeDir, _ := os.UserHomeDir()
	possiblePaths := []string{
		filepath.Join(homeDir, "AppData", "Local", "Programs", "Microsoft VS Code", "Code.exe"),
		"C:\\Program Files\\Microsoft VS Code\\Code.exe",
		"C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe",
	}

	for _, p := range possiblePaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	return ""
}

// detectCursor 检测Cursor
func (a *App) detectCursor() string {
	// 尝试从PATH找到cursor命令
	if path, err := exec.LookPath("cursor"); err == nil {
		return path
	}

	homeDir, _ := os.UserHomeDir()
	possiblePaths := []string{
		filepath.Join(homeDir, "AppData", "Local", "Programs", "Cursor", "Cursor.exe"),
		filepath.Join(homeDir, "AppData", "Local", "cursor", "Cursor.exe"),
	}

	for _, p := range possiblePaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	return ""
}

// detectWindsurf 检测Windsurf
func (a *App) detectWindsurf() string {
	// 尝试从PATH找到windsurf命令
	if path, err := exec.LookPath("windsurf"); err == nil {
		return path
	}

	homeDir, _ := os.UserHomeDir()
	possiblePaths := []string{
		filepath.Join(homeDir, "AppData", "Local", "Programs", "Windsurf", "Windsurf.exe"),
		filepath.Join(homeDir, "AppData", "Local", "windsurf", "Windsurf.exe"),
	}

	for _, p := range possiblePaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	return ""
}

// detectPyCharm 检测PyCharm
func (a *App) detectPyCharm() string {
	homeDir, _ := os.UserHomeDir()

	// JetBrains Toolbox常见路径
	toolboxPath := filepath.Join(homeDir, "AppData", "Local", "JetBrains", "Toolbox", "apps", "PyCharm-P")
	if info, err := os.Stat(toolboxPath); err == nil && info.IsDir() {
		// 查找最新版本
		entries, _ := os.ReadDir(toolboxPath)
		for i := len(entries) - 1; i >= 0; i-- {
			if entries[i].IsDir() {
				exePath := filepath.Join(toolboxPath, entries[i].Name(), "bin", "pycharm64.exe")
				if _, err := os.Stat(exePath); err == nil {
					return exePath
				}
			}
		}
	}

	// 标准安装路径
	possiblePaths := []string{
		"C:\\Program Files\\JetBrains\\PyCharm\\bin\\pycharm64.exe",
		"C:\\Program Files (x86)\\JetBrains\\PyCharm\\bin\\pycharm64.exe",
	}

	for _, p := range possiblePaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	return ""
}

// detectSublimeText 检测Sublime Text
func (a *App) detectSublimeText() string {
	// 尝试从PATH找到subl命令
	if path, err := exec.LookPath("subl"); err == nil {
		return path
	}

	possiblePaths := []string{
		"C:\\Program Files\\Sublime Text\\sublime_text.exe",
		"C:\\Program Files\\Sublime Text 3\\sublime_text.exe",
		"C:\\Program Files (x86)\\Sublime Text\\sublime_text.exe",
	}

	for _, p := range possiblePaths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}

	return ""
}

// OpenInIDE 使用指定IDE打开文件
func (a *App) OpenInIDE(idePath, filePath string) error {
	// 确保文件存在
	if _, err := os.Stat(filePath); err != nil {
		return fmt.Errorf("文件不存在: %s", filePath)
	}

	// 根据IDE路径判断使用哪个命令
	var cmd *exec.Cmd

	if strings.Contains(strings.ToLower(idePath), "code") {
		// VSCode
		cmd = exec.Command(idePath, filePath)
	} else if strings.Contains(strings.ToLower(idePath), "cursor") {
		// Cursor
		cmd = exec.Command(idePath, filePath)
	} else if strings.Contains(strings.ToLower(idePath), "windsurf") {
		// Windsurf
		cmd = exec.Command(idePath, filePath)
	} else if strings.Contains(strings.ToLower(idePath), "pycharm") {
		// PyCharm
		cmd = exec.Command(idePath, "--line", "1", filePath)
	} else if strings.Contains(strings.ToLower(idePath), "sublime") {
		// Sublime Text
		cmd = exec.Command(idePath, filePath)
	} else {
		// 默认方式
		cmd = exec.Command(idePath, filePath)
	}

	// 异步启动，不等待完成
	err := cmd.Start()
	if err != nil {
		return fmt.Errorf("打开IDE失败: %v", err)
	}

	return nil
}

// ========== AI 配置管理 ==========

// AIConfig AI配置
type AIConfig struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Provider    string    `json:"provider"`
	BaseURL     string    `json:"baseUrl"`
	APIKey      string    `json:"apiKey"`
	Model       string    `json:"model"`
	Temperature float32   `json:"temperature"`
	MaxTokens   int       `json:"maxTokens"`
	IsDefault   bool      `json:"isDefault"`
	CreatedAt   time.Time `json:"createdAt"`
	UpdatedAt   time.Time `json:"updatedAt"`
}

// OpenAIRequest OpenAI兼容API请求
type OpenAIRequest struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	Temperature float32   `json:"temperature"`
	MaxTokens   int       `json:"max_tokens,omitempty"`
}

// Message 消息
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// OpenAIResponse OpenAI兼容API响应
type OpenAIResponse struct {
	Choices []struct {
		Message Message `json:"message"`
	} `json:"choices"`
}

// GetAIConfigs 获取所有AI配置
func (a *App) GetAIConfigs() []AIConfig {
	configs := []AIConfig{}
	configPath := filepath.Join(a.projectsDir, "ai_config.json")

	data, err := os.ReadFile(configPath)
	if err != nil {
		return configs
	}

	json.Unmarshal(data, &configs)
	return configs
}

// SaveAIConfigs 保存AI配置列表
func (a *App) SaveAIConfigs(configs []AIConfig) error {
	configPath := filepath.Join(a.projectsDir, "ai_config.json")
	data, err := json.MarshalIndent(configs, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(configPath, data, 0644)
}

// GetDefaultAIConfig 获取默认AI配置
func (a *App) GetDefaultAIConfig() *AIConfig {
	configs := a.GetAIConfigs()
	for i := range configs {
		if configs[i].IsDefault {
			return &configs[i]
		}
	}
	if len(configs) > 0 {
		return &configs[0]
	}
	return nil
}

// CreateAIConfig 创建AI配置
func (a *App) CreateAIConfig(name, provider, baseURL, apiKey, model string, temperature float32, maxTokens int) (*AIConfig, error) {
	configs := a.GetAIConfigs()

	config := AIConfig{
		ID:          fmt.Sprintf("%d", time.Now().UnixNano()),
		Name:        name,
		Provider:    provider,
		BaseURL:     baseURL,
		APIKey:      apiKey,
		Model:       model,
		Temperature: temperature,
		MaxTokens:   maxTokens,
		IsDefault:   len(configs) == 0, // 第一个配置自动设为默认
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	configs = append(configs, config)
	if err := a.SaveAIConfigs(configs); err != nil {
		return nil, err
	}

	return &config, nil
}

// UpdateAIConfig 更新AI配置
func (a *App) UpdateAIConfig(id, name, provider, baseURL, apiKey, model string, temperature float32, maxTokens int) error {
	configs := a.GetAIConfigs()

	for i := range configs {
		if configs[i].ID == id {
			configs[i].Name = name
			configs[i].Provider = provider
			configs[i].BaseURL = baseURL
			configs[i].APIKey = apiKey
			configs[i].Model = model
			configs[i].Temperature = temperature
			configs[i].MaxTokens = maxTokens
			configs[i].UpdatedAt = time.Now()
			break
		}
	}

	return a.SaveAIConfigs(configs)
}

// DeleteAIConfig 删除AI配置
func (a *App) DeleteAIConfig(id string) error {
	configs := a.GetAIConfigs()
	newConfigs := []AIConfig{}

	for _, config := range configs {
		if config.ID != id {
			newConfigs = append(newConfigs, config)
		}
	}

	return a.SaveAIConfigs(newConfigs)
}

// SetDefaultAIConfig 设置默认AI配置
func (a *App) SetDefaultAIConfig(id string) error {
	configs := a.GetAIConfigs()

	for i := range configs {
		configs[i].IsDefault = (configs[i].ID == id)
	}

	return a.SaveAIConfigs(configs)
}

// TestAIConnection 测试AI连接
func (a *App) TestAIConnection(baseURL, apiKey, model string) (string, error) {
	a.LogInfo(fmt.Sprintf("测试AI连接: URL=%s, Model=%s", baseURL, model))

	// 构建测试请求
	reqBody := OpenAIRequest{
		Model: model,
		Messages: []Message{
			{Role: "user", Content: "你好"},
		},
		Temperature: 0.7,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		a.LogError(fmt.Sprintf("构建测试请求失败: %v", err))
		return "", fmt.Errorf("构建请求失败: %v", err)
	}

	// 发送HTTP请求
	url := strings.TrimSuffix(baseURL, "/") + "/chat/completions"
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		a.LogError(fmt.Sprintf("创建测试请求失败: %v", err))
		return "", fmt.Errorf("创建请求失败: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		a.LogError(fmt.Sprintf("连接AI服务失败: %v", err))
		return "", fmt.Errorf("连接失败: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		a.LogError(fmt.Sprintf("AI服务返回错误 (%d): %s", resp.StatusCode, string(body)))
		return "", fmt.Errorf("API返回错误 (%d): %s", resp.StatusCode, string(body))
	}

	a.LogInfo("AI连接测试成功")
	return "连接成功！", nil
}

// AnalyzeCode AI代码分析
func (a *App) AnalyzeCode(code, configID string) (string, error) {
	a.LogInfo("开始执行AI代码分析...")

	// 获取AI配置
	var config *AIConfig
	if configID == "" {
		config = a.GetDefaultAIConfig()
	} else {
		configs := a.GetAIConfigs()
		for i := range configs {
			if configs[i].ID == configID {
				config = &configs[i]
				break
			}
		}
	}

	if config == nil {
		a.LogError("AI分析失败: 未找到AI配置")
		return "", fmt.Errorf("未找到AI配置，请先配置AI")
	}

	a.LogInfo(fmt.Sprintf("使用AI配置: %s (%s)", config.Name, config.Model))

	// 构建分析提示词
	prompt := fmt.Sprintf(`你是一个专业的Python代码专家。请优化以下代码：

%s

请直接给出完整的、经过优化的代码结果。
要求：
1. 代码应该是完整的，可以直接复制使用。
2. 包含必要的中文注释。
3. 修复潜在的 bug 和性能问题。
4. 保持原有的功能逻辑不变，除非有明显的错误。
5. 输出格式要求：请使用Markdown代码块包裹代码，并在代码块之前简要说明（1-2句话）做了哪些主要优化。`, code)

	// 构建请求
	reqBody := OpenAIRequest{
		Model: config.Model,
		Messages: []Message{
			{Role: "user", Content: prompt},
		},
		Temperature: config.Temperature,
	}

	if config.MaxTokens > 0 {
		reqBody.MaxTokens = config.MaxTokens
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		a.LogError(fmt.Sprintf("构建请求失败: %v", err))
		return "", fmt.Errorf("构建请求失败: %v", err)
	}

	// 发送HTTP请求
	url := strings.TrimSuffix(config.BaseURL, "/") + "/chat/completions"
	a.LogInfo(fmt.Sprintf("发送请求至: %s", url))

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		a.LogError(fmt.Sprintf("创建请求失败: %v", err))
		return "", fmt.Errorf("创建请求失败: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+config.APIKey)

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		a.LogError(fmt.Sprintf("API请求失败: %v", err))
		return "", fmt.Errorf("请求失败: %v", err)
	}
	defer resp.Body.Close()

	// 读取响应内容
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		a.LogError(fmt.Sprintf("读取响应失败: %v", err))
		return "", fmt.Errorf("读取响应失败: %v", err)
	}

	// 检查状态码
	if resp.StatusCode != http.StatusOK {
		bodyStr := string(body)
		a.LogError(fmt.Sprintf("API返回错误 (%d): %s", resp.StatusCode, bodyStr))
		return "", fmt.Errorf("API返回错误 (%d): %s", resp.StatusCode, bodyStr)
	}

	// 解析响应
	var apiResp OpenAIResponse
	if err := json.Unmarshal(body, &apiResp); err != nil {
		// 解析失败，记录原始响应内容以便排查
		a.LogError(fmt.Sprintf("解析JSON响应失败: %v. 原始响应: %s", err, string(body)))
		return "", fmt.Errorf("解析响应失败: %v", err)
	}

	if len(apiResp.Choices) == 0 {
		a.LogError("API返回空响应: choices为空")
		return "", fmt.Errorf("API返回空响应")
	}

	a.LogInfo("AI分析完成")
	return apiResp.Choices[0].Message.Content, nil
}

// ========== 执行日志管理 ==========

// getExecutionLogsPath 获取执行日志文件路径
func (a *App) getExecutionLogsPath() string {
	return filepath.Join(a.projectsDir, "execution_logs.json")
}

// loadExecutionLogs 加载所有执行日志
func (a *App) loadExecutionLogs() ([]ExecutionLog, error) {
	logsPath := a.getExecutionLogsPath()

	if _, err := os.Stat(logsPath); os.IsNotExist(err) {
		return []ExecutionLog{}, nil
	}

	data, err := os.ReadFile(logsPath)
	if err != nil {
		return nil, fmt.Errorf("读取执行日志文件失败: %v", err)
	}

	var logs []ExecutionLog
	if err := json.Unmarshal(data, &logs); err != nil {
		return nil, fmt.Errorf("解析执行日志失败: %v", err)
	}

	return logs, nil
}

// saveExecutionLogs 保存所有执行日志
func (a *App) saveExecutionLogs(logs []ExecutionLog) error {
	logsPath := a.getExecutionLogsPath()

	data, err := json.MarshalIndent(logs, "", "  ")
	if err != nil {
		return fmt.Errorf("序列化执行日志失败: %v", err)
	}

	if err := os.WriteFile(logsPath, data, 0644); err != nil {
		return fmt.Errorf("写入执行日志文件失败: %v", err)
	}

	return nil
}

// CreateExecutionLog 创建执行日志（执行开始时调用）
func (a *App) CreateExecutionLog(projectID, projectName, scriptName, scriptPath, scriptContent, command string, variables map[string]string) (string, error) {
	logs, err := a.loadExecutionLogs()
	if err != nil {
		a.LogError(fmt.Sprintf("加载执行日志失败: %v", err))
		logs = []ExecutionLog{}
	}

	// 生成唯一 ID
	logID := fmt.Sprintf("%d", time.Now().UnixNano())

	newLog := ExecutionLog{
		ID:            logID,
		ProjectID:     projectID,
		ProjectName:   projectName,
		ScriptName:    scriptName,
		ScriptPath:    scriptPath,
		ScriptContent: scriptContent,
		Command:       command,
		Variables:     variables,
		StartTime:     time.Now().Unix(),
		EndTime:       0,
		Status:        "running",
		Output:        "",
	}

	// 添加到列表开头（最新的在前面）
	logs = append([]ExecutionLog{newLog}, logs...)

	// 限制日志数量（保留最近 500 条）
	if len(logs) > 500 {
		logs = logs[:500]
	}

	if err := a.saveExecutionLogs(logs); err != nil {
		return "", err
	}

	a.LogInfo(fmt.Sprintf("创建执行日志: %s - %s", projectName, scriptName))
	return logID, nil
}

// UpdateExecutionLog 更新执行日志（执行完成时调用）
func (a *App) UpdateExecutionLog(logID string, status string, output string) error {
	logs, err := a.loadExecutionLogs()
	if err != nil {
		return err
	}

	for i, log := range logs {
		if log.ID == logID {
			logs[i].Status = status
			logs[i].Output = output
			logs[i].EndTime = time.Now().Unix()
			break
		}
	}

	return a.saveExecutionLogs(logs)
}

// GetExecutionLogs 获取执行日志列表（支持按项目筛选）
func (a *App) GetExecutionLogs(projectID string, limit int) ([]ExecutionLog, error) {
	logs, err := a.loadExecutionLogs()
	if err != nil {
		return nil, err
	}

	// 按项目筛选
	if projectID != "" {
		filtered := []ExecutionLog{}
		for _, log := range logs {
			if log.ProjectID == projectID {
				filtered = append(filtered, log)
			}
		}
		logs = filtered
	}

	// 限制返回数量
	if limit > 0 && len(logs) > limit {
		logs = logs[:limit]
	}

	return logs, nil
}

// GetExecutionLogDetail 获取单条日志详情
func (a *App) GetExecutionLogDetail(logID string) (*ExecutionLog, error) {
	logs, err := a.loadExecutionLogs()
	if err != nil {
		return nil, err
	}

	for _, log := range logs {
		if log.ID == logID {
			return &log, nil
		}
	}

	return nil, fmt.Errorf("日志不存在: %s", logID)
}

// DeleteExecutionLog 删除单条日志
func (a *App) DeleteExecutionLog(logID string) error {
	logs, err := a.loadExecutionLogs()
	if err != nil {
		return err
	}

	filtered := []ExecutionLog{}
	for _, log := range logs {
		if log.ID != logID {
			filtered = append(filtered, log)
		}
	}

	return a.saveExecutionLogs(filtered)
}

// ClearExecutionLogs 清空执行日志（支持按项目清空）
func (a *App) ClearExecutionLogs(projectID string) error {
	if projectID == "" {
		// 清空所有
		return a.saveExecutionLogs([]ExecutionLog{})
	}

	// 只清空指定项目的日志
	logs, err := a.loadExecutionLogs()
	if err != nil {
		return err
	}

	filtered := []ExecutionLog{}
	for _, log := range logs {
		if log.ProjectID != projectID {
			filtered = append(filtered, log)
		}
	}

	return a.saveExecutionLogs(filtered)
}

// ========== 文件选择对话框 ==========

// SelectFile 打开文件选择对话框
func (a *App) SelectFile(title string, filterPattern string, filterDisplay string) (string, error) {
	filters := []runtime.FileFilter{}

	if filterPattern != "" {
		filters = append(filters, runtime.FileFilter{
			DisplayName: filterDisplay,
			Pattern:     filterPattern,
		})
	}

	// 添加所有文件选项
	filters = append(filters, runtime.FileFilter{
		DisplayName: "所有文件 (*.*)",
		Pattern:     "*.*",
	})

	filePath, err := runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{
		Title:   title,
		Filters: filters,
	})

	if err != nil {
		return "", err
	}

	return filePath, nil
}

// SelectModelFile 选择模型文件（预设模型文件过滤器）
func (a *App) SelectModelFile() (string, error) {
	return a.SelectFile(
		"选择模型文件",
		"*.safetensors;*.ckpt;*.pt;*.pth;*.bin",
		"模型文件 (*.safetensors, *.ckpt, *.pt, *.pth, *.bin)",
	)
}
