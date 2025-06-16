import chalk from 'chalk';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export class Toast {
  static show(message: string, type: ToastType = 'info'): void {
    const icon = this.getIcon(type);
    const color = this.getColor(type);
    
    console.log(`${icon} ${color(message)}`);
  }

  private static getIcon(type: ToastType): string {
    switch (type) {
      case 'success':
        return '✓';
      case 'error':
        return '✗';
      case 'warning':
        return '⚠';
      case 'info':
      default:
        return 'ℹ';
    }
  }

  private static getColor(type: ToastType): (text: string) => string {
    switch (type) {
      case 'success':
        return chalk.green;
      case 'error':
        return chalk.red;
      case 'warning':
        return chalk.yellow;
      case 'info':
      default:
        return chalk.blue;
    }
  }
}