import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ProjectList from './pages/ProjectList';
import ProjectPanel from './pages/ProjectPanel';
import ModalApps from './pages/ModalApps';
import AIConfig from './pages/AIConfig';
import TemplateLibrary from './pages/TemplateLibrary';
import QuickActions from './pages/QuickActions';
import ScriptEditorPage from './pages/ScriptEditorPage';
import ComfyUIToolbox from './pages/ComfyUIToolbox';
import AuthorInfo from './pages/AuthorInfo';
import GlobalVariables from './pages/GlobalVariables';
import ExecutionLogs from './pages/ExecutionLogs';

function App() {
  return (
    <Router>
      <Routes>
        {/* 脚本编辑器页面不使用 Layout（全屏） */}
        <Route path="/script-editor/:projectId/:scriptPath" element={<ScriptEditorPage />} />
        
        {/* 其他页面使用 Layout */}
        <Route path="*" element={
          <Layout>
            <Routes>
              <Route path="/" element={<ProjectList />} />
              <Route path="/project/:id" element={<ProjectPanel />} />
              <Route path="/apps" element={<ModalApps />} />
              <Route path="/ai-config" element={<AIConfig />} />
              <Route path="/templates" element={<TemplateLibrary />} />
              <Route path="/quick-actions" element={<QuickActions />} />
              <Route path="/comfyui-toolbox" element={<ComfyUIToolbox />} />
              <Route path="/global-variables" element={<GlobalVariables />} />
              <Route path="/execution-logs" element={<ExecutionLogs />} />
              <Route path="/author" element={<AuthorInfo />} />
            </Routes>
          </Layout>
        } />
      </Routes>
    </Router>
  );
}

export default App;
