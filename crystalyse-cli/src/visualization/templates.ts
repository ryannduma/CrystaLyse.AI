import * as fs from 'fs';
import * as path from 'path';

export interface StructureData {
  composition: string;
  structure: string;
  format: 'cif' | 'xyz' | 'pdb' | 'mol';
  properties?: Record<string, any>;
  spaceGroup?: string;
  latticeParameters?: Record<string, number>;
  energy?: number;
  bandGap?: number;
}

export interface TemplateData {
  title: string;
  structure: StructureData;
  theme?: 'light' | 'dark';
  options?: {
    showUnitCell?: boolean;
    showLabels?: boolean;
    backgroundColor?: string;
    defaultStyle?: 'stick' | 'sphere' | 'cartoon' | 'surface';
  };
}

export interface CompareTemplateData {
  title: string;
  structures: StructureData[];
  theme?: 'light' | 'dark';
  options?: {
    showUnitCell?: boolean;
    showLabels?: boolean;
    backgroundColor?: string;
    defaultStyle?: 'stick' | 'sphere' | 'cartoon' | 'surface';
  };
}

export class TemplateRenderer {
  private static assetsPath = path.join(__dirname, '../../assets');

  static renderViewer(data: TemplateData): string {
    const template = this.loadTemplate('viewer.html');
    
    // Inject structure data
    const injectedData = {
      structure: data.structure.structure,
      format: data.structure.format,
      composition: data.structure.composition,
      properties: data.structure.properties || {},
      spaceGroup: data.structure.spaceGroup,
      latticeParameters: data.structure.latticeParameters,
      options: {
        showUnitCell: data.options?.showUnitCell || true,
        showLabels: data.options?.showLabels || false,
        backgroundColor: data.options?.backgroundColor || (data.theme === 'dark' ? '#1a1a1a' : 'white'),
        defaultStyle: data.options?.defaultStyle || 'stick'
      }
    };

    const html = template
      .replace('{{TITLE}}', data.title)
      .replace('{{THEME_CLASS}}', data.theme === 'dark' ? 'dark-theme' : 'light-theme')
      .replace('window.structureData || {}', JSON.stringify(injectedData, null, 2))
      .replace('{{STRUCTURE_INFO}}', this.generateStructureInfo(data.structure))
      .replace('{{PROPERTIES_LIST}}', this.generatePropertiesList(data.structure.properties || {}));

    return html;
  }

  static renderCompare(data: CompareTemplateData): string {
    const template = this.loadTemplate('compare.html');
    
    // Inject structures data
    const injectedData = {
      structures: data.structures.map(s => ({
        structure: s.structure,
        format: s.format,
        composition: s.composition,
        properties: s.properties || {},
        spaceGroup: s.spaceGroup,
        latticeParameters: s.latticeParameters
      })),
      options: {
        showUnitCell: data.options?.showUnitCell || true,
        showLabels: data.options?.showLabels || false,
        backgroundColor: data.options?.backgroundColor || (data.theme === 'dark' ? '#1a1a1a' : 'white'),
        defaultStyle: data.options?.defaultStyle || 'stick'
      }
    };

    const html = template
      .replace('{{TITLE}}', data.title)
      .replace('{{THEME_CLASS}}', data.theme === 'dark' ? 'dark-theme' : 'light-theme')
      .replace('window.structuresData || []', JSON.stringify(injectedData, null, 2))
      .replace('{{COMPARISON_INFO}}', this.generateComparisonInfo(data.structures));

    return html;
  }

  private static loadTemplate(templateName: string): string {
    const templatePath = path.join(this.assetsPath, templateName);
    try {
      return fs.readFileSync(templatePath, 'utf8');
    } catch (error) {
      throw new Error(`Failed to load template ${templateName}: ${(error as Error).message}`);
    }
  }

  private static generateStructureInfo(structure: StructureData): string {
    let info = '';
    
    if (structure.composition) {
      info += `<p><strong>Composition:</strong> ${structure.composition}</p>`;
    }
    
    if (structure.spaceGroup) {
      info += `<p><strong>Space Group:</strong> ${structure.spaceGroup}</p>`;
    }
    
    if (structure.latticeParameters) {
      const params = structure.latticeParameters;
      info += `<p><strong>Lattice Parameters:</strong></p>`;
      info += `<ul>`;
      if (params.a) info += `<li>a = ${params.a.toFixed(3)} Å</li>`;
      if (params.b) info += `<li>b = ${params.b.toFixed(3)} Å</li>`;
      if (params.c) info += `<li>c = ${params.c.toFixed(3)} Å</li>`;
      if (params.alpha) info += `<li>α = ${params.alpha.toFixed(1)}°</li>`;
      if (params.beta) info += `<li>β = ${params.beta.toFixed(1)}°</li>`;
      if (params.gamma) info += `<li>γ = ${params.gamma.toFixed(1)}°</li>`;
      info += `</ul>`;
    }
    
    return info || '<p>Structure loaded successfully</p>';
  }

  private static generatePropertiesList(properties: Record<string, any>): string {
    if (!properties || Object.keys(properties).length === 0) {
      return '<p>No properties available</p>';
    }
    
    let html = '<ul class="properties-list">';
    
    Object.entries(properties).forEach(([key, value]) => {
      const displayKey = key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
      let displayValue = value;
      
      if (typeof value === 'number') {
        if (key.includes('energy') || key.includes('Energy')) {
          displayValue = `${value.toFixed(3)} eV`;
        } else if (key.includes('gap') || key.includes('Gap')) {
          displayValue = `${value.toFixed(2)} eV`;
        } else {
          displayValue = value.toFixed(3);
        }
      }
      
      html += `<li><strong>${displayKey}:</strong> ${displayValue}</li>`;
    });
    
    html += '</ul>';
    return html;
  }

  private static generateComparisonInfo(structures: StructureData[]): string {
    let info = `<p>Comparing ${structures.length} structures:</p><ul>`;
    
    structures.forEach((structure, index) => {
      info += `<li><strong>Structure ${index + 1}:</strong> ${structure.composition || 'Unknown composition'}</li>`;
    });
    
    info += '</ul>';
    return info;
  }

  static generateTempFilePath(prefix: string = 'crystalyse'): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return path.join(require('os').tmpdir(), `${prefix}_${timestamp}_${random}.html`);
  }
}