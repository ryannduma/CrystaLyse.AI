#!/usr/bin/env node

import { Command } from 'commander';
import { viewCommand } from './commands/view';
import { analyzeCommand } from './commands/analyze';
import { compareCommand } from './commands/compare';
import { Toast } from './ui/toasts';
import { CrystaLyseShell } from './shell';

const program = new Command();

program
  .name('crystalyse')
  .description('CLI for crystal structure analysis and visualization')
  .version('0.1.0');

// Add commands
program.addCommand(viewCommand);
program.addCommand(analyzeCommand);
program.addCommand(compareCommand);

// Add shell command
program
  .command('shell')
  .description('Start CrystaLyse.AI interactive shell')
  .action(() => {
    const shell = new CrystaLyseShell();
    shell.start();
  });

// Global error handler
program.configureOutput({
  writeErr: (str) => process.stderr.write(str)
});

process.on('uncaughtException', (error) => {
  Toast.show(`Unexpected error: ${error.message}`, 'error');
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  Toast.show(`Unhandled rejection: ${reason}`, 'error');
  process.exit(1);
});

// Parse command line arguments
program.parse(process.argv);

// Show help if no command is provided
if (!process.argv.slice(2).length) {
  program.outputHelp();
}