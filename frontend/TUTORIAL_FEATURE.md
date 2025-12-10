# Modal 教程功能

## ✨ 功能特性

已成功添加 Modal 使用教程页面，包含以下特性：

### 1. 可折叠侧边栏
- 左侧文档列表支持展开/收起
- 点击菜单按钮切换侧边栏显示状态
- 平滑的过渡动画效果

### 2. 文档分类
- **快速开始**: 安装配置、第一个应用
- **核心概念**: 镜像管理、GPU计算
- **存储管理**: Volume持久化、Secret管理
- **Web服务**: Web Endpoint、FastAPI集成
- **并行处理**: Map并行处理
- **最佳实践**: 成本优化、调试技巧

### 3. Markdown 渲染
- 完整的 Markdown 支持
- 代码高亮显示
- 表格、列表等格式支持
- 响应式布局

## 📁 文件结构

```
frontend/src/
├── pages/
│   └── ModalTutorial.tsx          # 教程页面主组件
├── data/
│   └── modalTutorials.ts          # 教程数据
└── components/
    └── Sidebar.tsx                 # 更新：添加教程入口
```

## 🚀 使用方法

### 访问教程

1. 启动应用后，在左侧导航栏找到 "学习" 分类
2. 点击 "Modal 教程" 进入教程页面
3. 使用左侧文档列表选择要查看的教程
4. 点击菜单按钮可以收起/展开侧边栏

### 添加新教程

编辑 `src/data/modalTutorials.ts`：

```typescript
{
  id: 'new-section',
  title: '新章节',
  children: [
    {
      id: 'new-tutorial',
      title: '新教程',
      content: `# 教程标题

## 内容

\`\`\`python
# 代码示例
import modal
\`\`\`
`
    }
  ]
}
```

## 🎨 样式说明

### Prose 样式
使用 Tailwind CSS Typography 插件提供的 prose 类：
- `prose`: 基础文章样式
- `prose-slate`: 配色方案
- `max-w-none`: 取消最大宽度限制

### 响应式设计
- 桌面端: 左侧320px侧边栏 + 右侧内容区
- 侧边栏收起时: 全宽内容显示
- 平滑过渡动画

## 📦 依赖

已添加的依赖：
- `@tailwindcss/typography`: Markdown 样式
- `react-markdown`: Markdown 渲染
- `react-syntax-highlighter`: 代码高亮
- `remark-gfm`: GitHub Flavored Markdown

## 🔧 安装依赖

```bash
cd frontend
npm install
```

## 💡 技术实现

### 1. 状态管理
使用 React Hooks 管理：
- `selectedTutorial`: 当前选中的教程
- `expandedSections`: 展开的章节集合
- `isSidebarOpen`: 侧边栏显示状态

### 2. Markdown 渲染
```typescript
<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  components={{
    code({ className, children }: any) {
      // 自定义代码块渲染
      return <SyntaxHighlighter>...</SyntaxHighlighter>
    }
  }}
>
  {content}
</ReactMarkdown>
```

### 3. 路由配置
```typescript
// 全屏页面，不使用 Layout
<Route path="/tutorial" element={<ModalTutorial />} />
```

## 📝 教程内容

当前包含以下教程主题：

1. **快速开始**
   - 安装与配置
   - 第一个应用

2. **核心概念**
   - 镜像管理
   - GPU 计算

3. **存储管理**
   - Volume 持久化存储
   - Secret 密钥管理

4. **Web 服务**
   - Web Endpoint
   - FastAPI 集成

5. **并行处理**
   - Map 并行处理

6. **最佳实践**
   - 成本优化
   - 调试技巧

## 🎯 未来扩展

可以继续添加的内容：
- 更多高级主题教程
- 实战案例分析
- 视频教程嵌入
- 交互式代码示例
- 搜索功能
- 收藏/书签功能
- 进度追踪
- 评论和反馈系统
