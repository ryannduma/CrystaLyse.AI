import * as readline from 'readline';
import { EventEmitter } from 'events';
import { PythonBridge } from './bridge/python';
import { ProgressIndicator } from './ui/progress';
import { Toast } from './ui/toasts';
import { QuickActions } from './ui/quickActions';
import { ViewerPreview } from './visualization/preview';
import { SessionManager } from './session';
import { CacheStrategy } from './cache/strategy';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

export interface ShellContext {
  session: SessionManager;
  bridge: PythonBridge;
  cache: CacheStrategy;
  viewer: ViewerPreview;
  currentResult?: any;
  mode: 'creative' | 'rigorous';
  autoView: boolean;
  history: string[];
}

export class CrystaLyseShell extends EventEmitter {
  private rl: readline.Interface;
  private context: ShellContext;
  private progress: ProgressIndicator;
  private isProcessing: boolean = false;

  constructor() {
    super();
    
    // Initialize context
    this.context = {
      session: new SessionManager(),
      bridge: new PythonBridge(),
      cache: new CacheStrategy({
        directory: path.join(os.homedir(), '.crystalyse', 'cache'),
        ttl: 3600000, // 1 hour
        maxSize: 100 * 1024 * 1024 // 100MB
      }),
      viewer: new ViewerPreview(),
      mode: 'rigorous',
      autoView: false,
      history: []
    };

    this.progress = new ProgressIndicator();
    
    // Setup readline interface
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      prompt: this.getPrompt(),
      completer: this.completer.bind(this),
      historySize: 1000
    });

    this.setupEventHandlers();
    this.loadConfiguration();
  }

  async start() {
    this.showWelcome();
    this.prompt();
  }

  private setupEventHandlers() {
    this.rl.on('line', (input) => {
      this.handleInput(input.trim());
    });

    this.rl.on('SIGINT', () => {
      if (this.isProcessing) {
        Toast.show('Cancelling current operation...', 'warning');
        this.context.bridge.cancel();
        this.isProcessing = false;
        this.prompt();
      } else {
        this.exit();
      }
    });

    this.rl.on('close', () => {
      this.exit();
    });

    // Handle bridge events
    this.context.bridge.on('data', (data) => {
      this.handlePythonOutput(data);
    });

    this.context.bridge.on('error', (error) => {
      Toast.show(`Python error: ${error.message}`, 'error');
      this.isProcessing = false;
      this.prompt();
    });

    this.context.bridge.on('complete', (result) => {
      this.handleAnalysisComplete(result);
    });
  }

  private getPrompt(): string {
    const modeSymbol = this.context.mode === 'rigorous' ? '🔬' : '🎨';
    return `${modeSymbol} crystalyse > `;
  }

  private showWelcome() {
    console.log(`
     ▄████▄   ██▀███ ▓██   ██▓  ██████ ▄▄▄█████▓ ▄▄▄       ██▓   ▓██   ██▓  ██████ ▓█████ 
    ▒██▀ ▀█  ▓██ ▒ ██▒▒██  ██▒▒██    ▒ ▓  ██▒ ▓▒▒████▄    ▓██▒    ▒██  ██▒▒██    ▒ ▓█   ▀ 
    ▒▓█    ▄ ▓██ ░▄█ ▒ ▒██ ██░░ ▓██▄   ▒ ▓██░ ▒░▒██  ▀█▄  ▒██░     ▒██ ██░░ ▓██▄   ▒███   
    ▒▓▓▄ ▄██▒▒██▀▀█▄   ░ ▐██▓░  ▒   ██▒░ ▓██▓ ░ ░██▄▄▄▄██ ▒██░     ░ ▐██▓░  ▒   ██▒▒▓█  ▄ 
    ▒ ▓███▀ ░░██▓ ▒██▒ ░ ██▒▓░▒██████▒▒  ▒██▒ ░  ▓█   ▓██▒░██████▒ ░ ██▒▓░▒██████▒▒░▒████▒
    ░ ░▒ ▒  ░░ ▒▓ ░▒▓░  ██▒▒▒ ▒ ▒▓▒ ▒ ░  ▒ ░░    ▒▒   ▓▒█░░ ▒░▓  ░  ██▒▒▒ ▒ ▒▓▒ ▒ ░░░ ▒░ ░
      ░  ▒     ░▒ ░ ▒░▓██ ░▒░ ░ ░▒  ░ ░    ░      ▒   ▒▒ ░░ ░ ▒  ░▓██ ░▒░ ░ ░▒  ░ ░ ░ ░  ░
    ░          ░░   ░ ▒ ▒ ░░  ░  ░  ░    ░        ░   ▒     ░ ░   ▒ ▒ ░░  ░  ░  ░     ░   
    ░ ░         ░     ░ ░           ░                 ░  ░    ░  ░░ ░           ░     ░  ░
    ░                 ░ ░                                         ░ ░                    
    
    Materials Intelligence at Your Fingertips
    Version 1.0.0 | Mode: ${this.context.mode} | Auto-view: ${this.context.autoView ? 'ON' : 'OFF'}
    
    Quick Start:
    • "Design a new battery cathode"
    • "Find materials with band gap 2-3 eV"
    • /help for all commands
    `);
  }

  private async handleInput(input: string) {
    if (!input) {
      this.prompt();
      return;
    }

    // Add to history
    this.context.history.push(input);

    // Handle commands
    if (input.startsWith('/')) {
      await this.handleCommand(input);
    } else {
      await this.handleQuery(input);
    }
  }

  private async handleCommand(command: string) {
    const [cmd, ...args] = command.split(' ');
    
    switch (cmd) {
      case '/help':
        this.showHelp();
        break;
      
      case '/mode':
        this.handleModeCommand(args[0]);
        break;
      
      case '/view':
        await this.handleViewCommand(args);
        break;
      
      case '/analyze':
        await this.handleAnalyzeCommand(args.join(' '));
        break;
      
      case '/compare':
        await this.handleCompareCommand(args);
        break;
      
      case '/save':
        await this.handleSaveCommand(args[0]);
        break;
      
      case '/load':
        await this.handleLoadCommand(args[0]);
        break;
      
      case '/history':
        this.showHistory();
        break;
      
      case '/status':
        this.showStatus();
        break;
      
      case '/config':
        await this.handleConfigCommand();
        break;
      
      case '/quick-view':
        this.context.autoView = !this.context.autoView;
        Toast.show(`Auto-view ${this.context.autoView ? 'enabled' : 'disabled'}`, 'info');
        break;
      
      case '/exit':
      case '/quit':
        this.exit();
        break;
      
      default:
        Toast.show(`Unknown command: ${cmd}. Type /help for available commands.`, 'warning');
    }
    
    this.prompt();
  }

  private async handleQuery(query: string) {
    if (this.isProcessing) {
      Toast.show('Please wait for the current analysis to complete', 'warning');
      this.prompt();
      return;
    }

    this.isProcessing = true;
    this.progress.start('Analyzing query...');

    try {
      // Use cache if available
      const cacheKey = `${this.context.mode}-${query}`;
      const cached = await this.context.cache.get<any>(cacheKey);
      
      if (cached) {
        this.progress.stop();
        Toast.show('Using cached result', 'info');
        this.handleAnalysisComplete(cached);
        return;
      }

      // Send to Python bridge
      const result = await this.context.bridge.analyze(query, this.context.mode);
      
      // Cache the result
      await this.context.cache.set<any>(cacheKey, result);
      
      this.handleAnalysisComplete(result);
      
    } catch (error) {
      this.progress.stop();
      Toast.show(`Analysis failed: ${(error as Error).message}`, 'error');
      this.isProcessing = false;
      this.prompt();
    }
  }

  private handleAnalysisComplete(result: any) {
    this.progress.stop();
    this.isProcessing = false;
    this.context.currentResult = result;
    
    // Display result
    this.displayResult(result);
    
    // Auto-view if enabled
    if (this.context.autoView && result.structure) {
      this.showQuickActions(result);
    } else {
      this.prompt();
    }
  }

  private displayResult(result: any) {
    console.log('\n' + '═'.repeat(60));
    console.log(`📊 Analysis Result`);
    console.log('═'.repeat(60));
    
    if (result.composition) {
      console.log(`🧪 Composition: ${result.composition}`);
    }
    
    if (result.properties) {
      console.log(`⚡ Properties:`);
      Object.entries(result.properties).forEach(([key, value]) => {
        console.log(`   • ${key}: ${value}`);
      });
    }
    
    if (result.structure) {
      console.log(`🔬 Structure: Available`);
    }
    
    console.log('═'.repeat(60) + '\n');
  }

  private async showQuickActions(result: any) {
    const actions = [
      { label: '[V]iew 3D', value: 'v', description: 'Open 3D viewer in browser' },
      { label: '[E]xport', value: 'e', description: 'Export structure data' },
      { label: '[S]ave', value: 's', description: 'Save to session' },
      { label: '[C]ontinue', value: 'c', description: 'Continue analysis' }
    ];
    
    try {
      const action = await QuickActions.prompt('Quick actions:', actions);
      
      switch (action) {
        case 'v':
          await this.context.viewer.showStructure(result.structure);
          break;
        case 'e':
          this.exportResult(result);
          break;
        case 's':
          this.saveResult(result);
          break;
        case 'c':
        default:
          break;
      }
    } catch (error) {
      // User cancelled or error occurred
    }
    
    this.prompt();
  }

  private async handleViewCommand(_args: string[]) {
    if (!this.context.currentResult?.structure) {
      Toast.show('No structure available to view', 'warning');
      return;
    }
    
    this.progress.start('Opening 3D viewer...');
    
    try {
      await this.context.viewer.showStructure(this.context.currentResult.structure);
      Toast.show('3D viewer opened in browser', 'success');
    } catch (error) {
      Toast.show(`Failed to open viewer: ${(error as Error).message}`, 'error');
    } finally {
      this.progress.stop();
    }
  }

  private async handleAnalyzeCommand(query: string) {
    if (!query) {
      Toast.show('Please provide a query to analyze', 'warning');
      return;
    }
    
    await this.handleQuery(query);
  }

  private async handleCompareCommand(args: string[]) {
    if (args.length < 2) {
      Toast.show('Please provide at least 2 structures to compare', 'warning');
      return;
    }
    
    // Implementation for structure comparison
    Toast.show('Comparison feature coming soon!', 'info');
  }

  private handleModeCommand(mode?: string) {
    if (!mode) {
      console.log(`Current mode: ${this.context.mode}`);
      return;
    }
    
    if (mode === 'creative' || mode === 'rigorous') {
      this.context.mode = mode;
      this.rl.setPrompt(this.getPrompt());
      Toast.show(`Mode changed to: ${mode}`, 'success');
    } else {
      Toast.show('Invalid mode. Use "creative" or "rigorous"', 'warning');
    }
  }

  private async handleSaveCommand(name?: string) {
    if (!name) {
      name = `session_${new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')}`;
    }
    
    try {
      await this.context.session.save(name, {
        history: this.context.history,
        mode: this.context.mode,
        currentResult: this.context.currentResult
      });
      Toast.show(`Session saved as: ${name}`, 'success');
    } catch (error) {
      Toast.show(`Failed to save session: ${(error as Error).message}`, 'error');
    }
  }

  private async handleLoadCommand(name?: string) {
    if (!name) {
      const sessions = await this.context.session.list();
      console.log('Available sessions:');
      sessions.forEach(session => console.log(`  • ${session}`));
      return;
    }
    
    try {
      const sessionData = await this.context.session.load(name);
      this.context.history = sessionData.history || [];
      this.context.mode = sessionData.mode || 'rigorous';
      this.context.currentResult = sessionData.currentResult;
      
      this.rl.setPrompt(this.getPrompt());
      Toast.show(`Session loaded: ${name}`, 'success');
    } catch (error) {
      Toast.show(`Failed to load session: ${(error as Error).message}`, 'error');
    }
  }

  private showHistory() {
    console.log('\n📜 Command History:');
    this.context.history.slice(-20).forEach((cmd, i) => {
      console.log(`  ${i + 1}. ${cmd}`);
    });
    console.log();
  }

  private async showStatus() {
    console.log('\n📊 System Status:');
    console.log(`  Mode: ${this.context.mode}`);
    console.log(`  Auto-view: ${this.context.autoView ? 'ON' : 'OFF'}`);
    console.log(`  Bridge Status: ${this.context.bridge.isConnected() ? 'Connected' : 'Disconnected'}`);
    console.log(`  Cache Size: ${await this.context.cache.size()} bytes`);
    console.log(`  History: ${this.context.history.length} commands`);
    console.log();
  }

  private async handleConfigCommand() {
    // Open configuration in editor
    Toast.show('Configuration editing coming soon!', 'info');
  }

  private showHelp() {
    console.log(`
📖 CrystaLyse.AI Commands:

Analysis Commands:
  /analyze <query>       - Analyze materials query
  /screen <criteria>     - Batch screening mode
  /predict <formula>     - Quick structure prediction
  /validate <composition>- SMACT validation only

Visualization Commands:
  /view [structure]      - Open 3D structure in browser
  /compare <s1> <s2>     - Side-by-side comparison
  /export <format>       - Export results

Workflow Commands:
  /mode [creative|rigorous] - Switch analysis modes
  /quick-view            - Toggle auto-view after analysis

Session Commands:
  /save [name]           - Save current session
  /load <session>        - Load previous session
  /history               - Show command history

System Commands:
  /config                - View/edit configuration
  /status                - System status
  /help                  - Show this help
  /exit                  - Exit CrystaLyse

Natural Language:
  Just type your materials query directly!
  Example: "Design a battery cathode material"
    `);
  }

  private async completer(line: string): Promise<[string[], string]> {
    const completions = [
      '/analyze', '/screen', '/predict', '/validate',
      '/view', '/compare', '/export',
      '/mode', '/quick-view', '/workflow',
      '/save', '/load', '/history',
      '/config', '/status', '/help', '/exit'
    ];
    
    const hits = completions.filter((c) => c.startsWith(line));
    return [hits.length ? hits : completions, line];
  }

  private handlePythonOutput(data: any) {
    // Handle streaming output from Python
    if (data.type === 'progress') {
      this.progress.update(data.message, data.percent);
    } else if (data.type === 'status') {
      this.progress.setStatus(data.message);
    }
  }

  private exportResult(_result: any) {
    // Implementation for exporting results
    Toast.show('Export feature coming soon!', 'info');
  }

  private saveResult(_result: any) {
    // Implementation for saving individual results
    Toast.show('Individual result saving coming soon!', 'info');
  }

  private loadConfiguration() {
    // Load CRYSTALYSE.md configuration if it exists
    const configPath = path.join(process.cwd(), 'CRYSTALYSE.md');
    if (fs.existsSync(configPath)) {
      try {
        const config = fs.readFileSync(configPath, 'utf8');
        // Parse configuration
        if (config.includes('mode: creative')) {
          this.context.mode = 'creative';
        }
        if (config.includes('auto_view: true')) {
          this.context.autoView = true;
        }
      } catch (error) {
        // Ignore configuration errors
      }
    }
  }

  private prompt() {
    this.rl.prompt();
  }

  private exit() {
    console.log('\n👋 Goodbye! Thanks for using CrystaLyse.AI');
    this.context.bridge.disconnect();
    process.exit(0);
  }
}