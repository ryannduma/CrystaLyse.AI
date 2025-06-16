import { Command } from 'commander';

export const compareCommand = new Command('compare')
  .description('Compare multiple crystal structures')
  .argument('<files...>', 'Paths to crystal structure files to compare')
  .option('-m, --mode <mode>', 'Comparison mode (overlay, side-by-side)', 'side-by-side')
  .option('-o, --output <file>', 'Save comparison result to file')
  .action(async (files: string[], options: any) => {
    // TODO: Implement compare command
    console.log(`Comparing files:`, files);
    console.log(`Options:`, options);
  });