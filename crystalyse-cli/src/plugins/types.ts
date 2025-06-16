import { Command } from 'commander';

export interface Plugin {
  name: string;
  version: string;
  description?: string;
  commands?: PluginCommand[];
  hooks?: PluginHooks;
}

export interface PluginCommand {
  name: string;
  description: string;
  builder: (program: Command) => Command;
}

export interface PluginHooks {
  beforeCommand?: (commandName: string, options: any) => Promise<void>;
  afterCommand?: (commandName: string, result: any) => Promise<void>;
  onError?: (error: Error) => Promise<void>;
}

export interface PluginContext {
  config: any;
  cache: any;
  ui: {
    toast: (message: string, type: string) => void;
    progress: (text: string) => any;
    table: (data: any[][], options: any) => void;
  };
}

export abstract class BasePlugin implements Plugin {
  abstract name: string;
  abstract version: string;
  description?: string;

  protected context: PluginContext | null = null;

  setContext(context: PluginContext): void {
    this.context = context;
  }

  abstract initialize(): Promise<void>;
}