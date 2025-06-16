import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';

export interface PythonBridgeOptions {
  pythonPath?: string;
  crystalyseDir?: string;
}

export class PythonBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private options: PythonBridgeOptions;
  private connected: boolean = false;
  private currentOperation: string | null = null;

  constructor(options: PythonBridgeOptions = {}) {
    super();
    this.options = {
      pythonPath: options.pythonPath || 'python3',
      crystalyseDir: options.crystalyseDir || path.join(__dirname, '../../../..')
    };
  }

  async connect(): Promise<void> {
    if (this.connected) return;

    return new Promise((resolve, reject) => {
      // Start the CrystaLyse Python bridge script
      const bridgeScript = path.join(__dirname, 'crystalyse_bridge.py');
      
      this.process = spawn(this.options.pythonPath!, [bridgeScript, this.options.crystalyseDir!], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: this.options.crystalyseDir
      });

      let initBuffer = '';

      this.process!.stdout!.on('data', (data) => {
        const lines = data.toString().split('\n');
        
        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const message = JSON.parse(line);
            
            if (message.type === 'ready') {
              this.connected = true;
              resolve();
            } else if (message.type === 'data') {
              this.emit('data', message.payload);
            } else if (message.type === 'complete') {
              this.emit('complete', message.payload);
              this.currentOperation = null;
            } else if (message.type === 'error') {
              this.emit('error', new Error(message.message));
              this.currentOperation = null;
            }
          } catch (e) {
            // Non-JSON output, treat as raw data
            initBuffer += line;
          }
        }
      });

      this.process!.stderr!.on('data', (data) => {
        console.error('Python bridge stderr:', data.toString());
      });

      this.process!.on('close', (code) => {
        this.connected = false;
        this.process = null;
        if (code !== 0) {
          this.emit('error', new Error(`Python bridge exited with code ${code}`));
        }
      });

      this.process!.on('error', (err) => {
        this.connected = false;
        reject(err);
      });

      // Timeout for connection
      setTimeout(() => {
        if (!this.connected) {
          reject(new Error('Python bridge connection timeout'));
        }
      }, 10000);
    });
  }

  async analyze(query: string, mode: 'creative' | 'rigorous' = 'rigorous'): Promise<any> {
    if (!this.connected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      if (this.currentOperation) {
        reject(new Error('Another operation is in progress'));
        return;
      }

      this.currentOperation = 'analyze';
      
      const request = {
        type: 'analyze',
        query,
        mode,
        timestamp: Date.now()
      };

      // Listen for completion
      const onComplete = (result: any) => {
        this.off('complete', onComplete);
        this.off('error', onError);
        resolve(result);
      };

      const onError = (error: Error) => {
        this.off('complete', onComplete);
        this.off('error', onError);
        reject(error);
      };

      this.once('complete', onComplete);
      this.once('error', onError);

      // Send request
      this.process!.stdin!.write(JSON.stringify(request) + '\n');
    });
  }

  async validateComposition(composition: string): Promise<any> {
    if (!this.connected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      const request = {
        type: 'validate',
        composition,
        timestamp: Date.now()
      };

      const onComplete = (result: any) => {
        this.off('complete', onComplete);
        this.off('error', onError);
        resolve(result);
      };

      const onError = (error: Error) => {
        this.off('complete', onComplete);
        this.off('error', onError);
        reject(error);
      };

      this.once('complete', onComplete);
      this.once('error', onError);

      this.process!.stdin!.write(JSON.stringify(request) + '\n');
    });
  }

  cancel(): void {
    if (this.process && this.currentOperation) {
      this.process.kill('SIGTERM');
      this.currentOperation = null;
    }
  }

  isConnected(): boolean {
    return this.connected;
  }

  disconnect(): void {
    if (this.process) {
      this.process.kill('SIGTERM');
      this.process = null;
    }
    this.connected = false;
  }
}