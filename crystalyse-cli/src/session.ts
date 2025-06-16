import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

export interface SessionData {
  name: string;
  timestamp: Date;
  history: string[];
  mode: 'creative' | 'rigorous';
  currentResult?: any;
  metadata?: Record<string, any>;
}

export class SessionManager {
  private sessionDir: string;

  constructor() {
    this.sessionDir = path.join(os.homedir(), '.crystalyse', 'sessions');
    this.ensureSessionDir();
  }

  private async ensureSessionDir() {
    try {
      await fs.mkdir(this.sessionDir, { recursive: true });
    } catch (error) {
      // Directory might already exist
    }
  }

  async save(name: string, data: Partial<SessionData>): Promise<void> {
    const sessionData: SessionData = {
      name,
      timestamp: new Date(),
      history: [],
      mode: 'rigorous',
      ...data
    };

    const filePath = path.join(this.sessionDir, `${name}.json`);
    await fs.writeFile(filePath, JSON.stringify(sessionData, null, 2));
  }

  async load(name: string): Promise<SessionData> {
    const filePath = path.join(this.sessionDir, `${name}.json`);
    const data = await fs.readFile(filePath, 'utf8');
    return JSON.parse(data) as SessionData;
  }

  async list(): Promise<string[]> {
    try {
      const files = await fs.readdir(this.sessionDir);
      return files
        .filter(file => file.endsWith('.json'))
        .map(file => file.replace('.json', ''));
    } catch (error) {
      return [];
    }
  }

  async delete(name: string): Promise<void> {
    const filePath = path.join(this.sessionDir, `${name}.json`);
    await fs.unlink(filePath);
  }

  async exists(name: string): Promise<boolean> {
    const filePath = path.join(this.sessionDir, `${name}.json`);
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }
}