import ora from 'ora';

export interface ProgressOptions {
  text: string;
  spinner?: string;
}

export class Progress {
  private spinner: any;

  constructor(options: ProgressOptions) {
    this.spinner = ora({
      text: options.text,
      spinner: (options.spinner as any) || 'dots'
    });
  }

  start(): void {
    this.spinner.start();
  }

  update(text: string): void {
    this.spinner.text = text;
  }

  succeed(text?: string): void {
    this.spinner.succeed(text || this.spinner.text);
  }

  fail(text?: string): void {
    this.spinner.fail(text || this.spinner.text);
  }

  stop(): void {
    this.spinner.stop();
  }
}

export class ProgressBar {
  private _current: number = 0;
  private total: number;
  private width: number = 40;

  get current(): number {
    return this._current;
  }

  constructor(total: number) {
    this.total = total;
  }

  update(current: number, message?: string): void {
    this._current = current;
    const percentage = (current / this.total) * 100;
    const filled = Math.round((this.width * current) / this.total);
    const bar = '█'.repeat(filled) + '░'.repeat(this.width - filled);
    
    process.stdout.write(`\r${bar} ${percentage.toFixed(1)}% ${message || ''}`);
    
    if (current >= this.total) {
      console.log('');
    }
  }
}

export class ProgressIndicator {
  private spinner: any = null;
  private status: string = '';

  start(text: string = 'Processing...'): void {
    this.status = text;
    this.spinner = ora({
      text,
      spinner: 'dots' as any
    }).start();
  }

  update(text: string, percent?: number): void {
    if (this.spinner) {
      this.status = text;
      const displayText = percent !== undefined ? `${text} (${percent}%)` : text;
      this.spinner.text = displayText;
    }
  }

  setStatus(status: string): void {
    this.update(status);
  }

  succeed(text?: string): void {
    if (this.spinner) {
      this.spinner.succeed(text || this.status);
      this.spinner = null;
    }
  }

  fail(text?: string): void {
    if (this.spinner) {
      this.spinner.fail(text || this.status);
      this.spinner = null;
    }
  }

  stop(): void {
    if (this.spinner) {
      this.spinner.stop();
      this.spinner = null;
    }
  }

  isActive(): boolean {
    return this.spinner !== null;
  }
}