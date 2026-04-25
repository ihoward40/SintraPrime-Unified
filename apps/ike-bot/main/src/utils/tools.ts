import fs from 'fs';
import path from 'path';

/**
 * Load OpenAI Agent-compatible tool definitions from the agent-tools directory
 */

interface ToolDefinition {
  type: string;
  function: {
    name: string;
    description: string;
    parameters: any;
    returns?: any;
    api_endpoint?: string;
    implementation_note?: string;
  };
}

/**
 * Load a single tool definition from a JSON file
 */
export function loadTool(toolName: string): ToolDefinition | null {
  try {
    const toolPath = path.join(process.cwd(), 'agent-tools', `${toolName}.json`);
    const toolData = fs.readFileSync(toolPath, 'utf-8');
    return JSON.parse(toolData);
  } catch (error) {
    console.error(`Failed to load tool ${toolName}:`, error);
    return null;
  }
}

/**
 * Load all tool definitions from the agent-tools directory
 */
export function loadAllTools(): ToolDefinition[] {
  try {
    const toolsDir = path.join(process.cwd(), 'agent-tools');
    const files = fs.readdirSync(toolsDir);
    
    const tools: ToolDefinition[] = [];
    
    for (const file of files) {
      if (file.endsWith('.json')) {
        const toolPath = path.join(toolsDir, file);
        const toolData = fs.readFileSync(toolPath, 'utf-8');
        tools.push(JSON.parse(toolData));
      }
    }
    
    return tools;
  } catch (error) {
    console.error('Failed to load tools:', error);
    return [];
  }
}

/**
 * Get tool definitions formatted for OpenAI API
 */
export function getOpenAITools(): any[] {
  const tools = loadAllTools();
  return tools.map(tool => ({
    type: tool.type,
    function: {
      name: tool.function.name,
      description: tool.function.description,
      parameters: tool.function.parameters,
    },
  }));
}

/**
 * Get a tool definition by name
 */
export function getToolByName(name: string): ToolDefinition | null {
  return loadTool(name);
}

/**
 * List all available tool names
 */
export function listToolNames(): string[] {
  try {
    const toolsDir = path.join(process.cwd(), 'agent-tools');
    const files = fs.readdirSync(toolsDir);
    return files
      .filter(file => file.endsWith('.json'))
      .map(file => file.replace('.json', ''));
  } catch (error) {
    console.error('Failed to list tool names:', error);
    return [];
  }
}
