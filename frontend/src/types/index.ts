export interface Project {
  id: string;
  name: string;
  path: string;
  description: string;
  status: 'running' | 'stopped' | 'deploying';
  createdAt: string;
  updatedAt: string;
}

export interface Script {
  name: string;
  path: string;
  fullPath: string;
  description?: string;
  order?: number;
}

export interface CommandResult {
  success: boolean;
  output: string;
  error: string;
}

export interface IDEConfig {
  name: string;
  path: string;
  command: string;
  icon: string;
  enabled: boolean;
  detected: boolean;
}

export interface AIConfig {
  id: string;
  name: string;
  provider: string;
  baseUrl: string;
  apiKey: string;
  model: string;
  temperature: number;
  maxTokens: number;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CodeSnippet {
  id: string;
  title: string;
  description: string;
  code: string;
  category: string;
  tags: string[];
}

export interface CodeSnippetCategory {
  id: string;
  name: string;
  icon: string;
  description: string;
  snippets: CodeSnippet[];
}