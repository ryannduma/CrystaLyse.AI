import Table from 'cli-table3';
import chalk from 'chalk';

export interface TableOptions {
  head: string[];
  colWidths?: number[];
  style?: any;
}

export class TableRenderer {
  static render(data: any[][], options: TableOptions): void {
    const tableOptions: any = {
      head: options.head.map(h => chalk.bold(h)),
      style: options.style || {
        head: ['cyan'],
        border: ['grey']
      }
    };

    if (options.colWidths) {
      tableOptions.colWidths = options.colWidths;
    }

    const table = new Table(tableOptions);

    data.forEach(row => {
      table.push(row);
    });

    console.log(table.toString());
  }

  static renderObject(obj: Record<string, any>, title?: string): void {
    if (title) {
      console.log(chalk.bold.underline(title));
    }

    const table = new Table({
      style: {
        head: ['cyan'],
        border: ['grey']
      }
    });

    Object.entries(obj).forEach(([key, value]) => {
      table.push({ [chalk.bold(key)]: value });
    });

    console.log(table.toString());
  }
}