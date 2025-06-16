import * as fs from 'fs/promises';
import * as os from 'os';
import { spawn } from 'child_process';
import { TemplateRenderer, TemplateData, CompareTemplateData, StructureData } from './templates';

export interface ViewerOptions {
  theme?: 'light' | 'dark';
  autoOpen?: boolean;
  showUnitCell?: boolean;
  showLabels?: boolean;
  backgroundColor?: string;
  defaultStyle?: 'stick' | 'sphere' | 'cartoon' | 'surface';
}

export class ViewerPreview {
  private tempFiles: Set<string> = new Set();

  async showStructure(structure: StructureData, options: ViewerOptions = {}): Promise<string> {
    const templateData: TemplateData = {
      title: `CrystaLyse Viewer - ${structure.composition || 'Crystal Structure'}`,
      structure,
      theme: options.theme || 'light',
      options: {
        showUnitCell: options.showUnitCell ?? true,
        showLabels: options.showLabels ?? false,
        backgroundColor: options.backgroundColor ?? (options.theme === 'dark' ? '#1a1a1a' : 'white'),
        defaultStyle: options.defaultStyle ?? 'stick'
      }
    };

    const html = TemplateRenderer.renderViewer(templateData);
    const filePath = TemplateRenderer.generateTempFilePath('crystalyse_viewer');
    
    await fs.writeFile(filePath, html);
    this.tempFiles.add(filePath);

    if (options.autoOpen !== false) {
      await this.openInBrowser(filePath);
    }

    return filePath;
  }

  async compareStructures(structures: StructureData[], options: ViewerOptions = {}): Promise<string> {
    const templateData: CompareTemplateData = {
      title: `CrystaLyse Comparison - ${structures.length} Structures`,
      structures,
      theme: options.theme || 'light',
      options: {
        showUnitCell: options.showUnitCell ?? true,
        showLabels: options.showLabels ?? false,
        backgroundColor: options.backgroundColor ?? (options.theme === 'dark' ? '#1a1a1a' : 'white'),
        defaultStyle: options.defaultStyle ?? 'stick'
      }
    };

    const html = TemplateRenderer.renderCompare(templateData);
    const filePath = TemplateRenderer.generateTempFilePath('crystalyse_compare');
    
    await fs.writeFile(filePath, html);
    this.tempFiles.add(filePath);

    if (options.autoOpen !== false) {
      await this.openInBrowser(filePath);
    }

    return filePath;
  }

  private async openInBrowser(filePath: string): Promise<void> {
    const url = `file://${filePath}`;
    const platform = os.platform();

    let command: string;
    let args: string[];

    switch (platform) {
      case 'darwin': // macOS
        command = 'open';
        args = [url];
        break;
      case 'win32': // Windows
        command = 'start';
        args = ['', url];
        break;
      default: // Linux and others
        command = 'xdg-open';
        args = [url];
        break;
    }

    return new Promise((resolve, reject) => {
      const process = spawn(command, args, { 
        detached: true, 
        stdio: 'ignore',
        shell: platform === 'win32'
      });

      process.on('error', (_error) => {
        // Try alternative browsers
        this.tryAlternativeBrowsers(url).then(resolve).catch(reject);
      });

      process.on('spawn', () => {
        process.unref();
        resolve();
      });

      // Timeout fallback
      setTimeout(() => {
        resolve();
      }, 2000);
    });
  }

  private async tryAlternativeBrowsers(url: string): Promise<void> {
    const browsers = [
      'google-chrome',
      'chrome',
      'chromium',
      'firefox',
      'safari',
      'microsoft-edge',
      'edge'
    ];

    for (const browser of browsers) {
      try {
        await new Promise((resolve, reject) => {
          const process = spawn(browser, [url], { 
            detached: true, 
            stdio: 'ignore' 
          });
          
          process.on('error', reject);
          process.on('spawn', () => {
            process.unref();
            resolve(undefined);
          });
        });
        return;
      } catch (error) {
        continue;
      }
    }

    throw new Error('Could not open browser. Please open the file manually: ' + url);
  }

  async cleanupTempFiles(): Promise<void> {
    for (const filePath of this.tempFiles) {
      try {
        await fs.unlink(filePath);
      } catch (error) {
        // Ignore cleanup errors
      }
    }
    this.tempFiles.clear();
  }

  getTempFiles(): string[] {
    return Array.from(this.tempFiles);
  }

  static async createStructureFromCIF(cifData: string, composition?: string): Promise<StructureData> {
    const structureData: StructureData = {
      composition: composition || 'Unknown',
      structure: cifData,
      format: 'cif',
      properties: {}
    };

    const spaceGroup = ViewerPreview.extractSpaceGroupFromCIF(cifData);
    if (spaceGroup) {
      structureData.spaceGroup = spaceGroup;
    }

    const latticeParams = ViewerPreview.extractLatticeParametersFromCIF(cifData);
    if (latticeParams) {
      structureData.latticeParameters = latticeParams;
    }

    return structureData;
  }

  static async createStructureFromXYZ(xyzData: string, composition?: string): Promise<StructureData> {
    return {
      composition: composition || 'Unknown',
      structure: xyzData,
      format: 'xyz',
      properties: {}
    };
  }

  private static extractSpaceGroupFromCIF(cifData: string): string | undefined {
    const lines = cifData.split('\n');
    for (const line of lines) {
      if (line.trim().startsWith('_space_group_name_H-M_alt') || 
          line.trim().startsWith('_symmetry_space_group_name_H-M')) {
        const match = line.match(/['"]([^'"]+)['"]/);
        if (match) {
          return match[1];
        }
      }
    }
    return undefined;
  }

  private static extractLatticeParametersFromCIF(cifData: string): Record<string, number> | undefined {
    const params: Record<string, number> = {};
    const lines = cifData.split('\n');
    
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('_cell_length_a')) {
        const match = trimmed.match(/[\d.]+/);
        if (match) params.a = parseFloat(match[0]);
      } else if (trimmed.startsWith('_cell_length_b')) {
        const match = trimmed.match(/[\d.]+/);
        if (match) params.b = parseFloat(match[0]);
      } else if (trimmed.startsWith('_cell_length_c')) {
        const match = trimmed.match(/[\d.]+/);
        if (match) params.c = parseFloat(match[0]);
      } else if (trimmed.startsWith('_cell_angle_alpha')) {
        const match = trimmed.match(/[\d.]+/);
        if (match) params.alpha = parseFloat(match[0]);
      } else if (trimmed.startsWith('_cell_angle_beta')) {
        const match = trimmed.match(/[\d.]+/);
        if (match) params.beta = parseFloat(match[0]);
      } else if (trimmed.startsWith('_cell_angle_gamma')) {
        const match = trimmed.match(/[\d.]+/);
        if (match) params.gamma = parseFloat(match[0]);
      }
    }
    
    return Object.keys(params).length > 0 ? params : undefined;
  }
}