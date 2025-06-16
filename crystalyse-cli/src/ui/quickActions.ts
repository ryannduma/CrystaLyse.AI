import * as inquirer from 'inquirer';

export interface QuickAction {
  label: string;
  value: string;
  description?: string;
}

export class QuickActions {
  static async prompt(
    message: string,
    actions: QuickAction[]
  ): Promise<string> {
    const { action } = await inquirer.prompt([
      {
        type: 'list',
        name: 'action',
        message,
        choices: actions.map(a => ({
          name: a.description ? `${a.label} - ${a.description}` : a.label,
          value: a.value
        }))
      }
    ]);
    
    return action;
  }

  static async confirm(message: string): Promise<boolean> {
    const { confirmed } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'confirmed',
        message,
        default: false
      }
    ]);
    
    return confirmed;
  }
}