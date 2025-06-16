import * as fs from 'fs-extra';
import * as path from 'path';
import * as crypto from 'crypto';

export interface CacheOptions {
  directory: string;
  ttl?: number; // Time to live in milliseconds
  maxSize?: number; // Max cache size in bytes
}

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  size: number;
}

export class CacheStrategy {
  private options: CacheOptions;

  constructor(options: CacheOptions) {
    this.options = {
      directory: options.directory,
      ttl: options.ttl || 3600000, // 1 hour default
      maxSize: options.maxSize || 100 * 1024 * 1024 // 100MB default
    };
    
    fs.ensureDirSync(this.options.directory);
  }

  async get<T>(key: string): Promise<T | null> {
    const filePath = this.getFilePath(key);
    
    if (!await fs.pathExists(filePath)) {
      return null;
    }

    try {
      const entry: CacheEntry<T> = await fs.readJson(filePath);
      
      // Check if entry is expired
      if (this.options.ttl && Date.now() - entry.timestamp > this.options.ttl) {
        await this.delete(key);
        return null;
      }
      
      return entry.data;
    } catch (error) {
      return null;
    }
  }

  async set<T>(key: string, data: T): Promise<void> {
    const filePath = this.getFilePath(key);
    const dataStr = JSON.stringify(data);
    
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      size: Buffer.byteLength(dataStr)
    };

    await fs.writeJson(filePath, entry);
    
    // Check cache size and clean if needed
    await this.cleanIfNeeded();
  }

  async delete(key: string): Promise<void> {
    const filePath = this.getFilePath(key);
    await fs.remove(filePath);
  }

  async clear(): Promise<void> {
    await fs.emptyDir(this.options.directory);
  }

  private getFilePath(key: string): string {
    const hash = crypto.createHash('md5').update(key).digest('hex');
    return path.join(this.options.directory, `${hash}.json`);
  }

  async size(): Promise<number> {
    try {
      const files = await fs.readdir(this.options.directory);
      let totalSize = 0;
      
      for (const file of files) {
        const filePath = path.join(this.options.directory, file);
        const stats = await fs.stat(filePath);
        totalSize += stats.size;
      }
      
      return totalSize;
    } catch (error) {
      return 0;
    }
  }

  async count(): Promise<number> {
    try {
      const files = await fs.readdir(this.options.directory);
      return files.length;
    } catch (error) {
      return 0;
    }
  }

  private async cleanIfNeeded(): Promise<void> {
    if (!this.options.maxSize) return;

    const files = await fs.readdir(this.options.directory);
    let totalSize = 0;
    const fileStats: Array<{ file: string; size: number; mtime: Date }> = [];

    for (const file of files) {
      const filePath = path.join(this.options.directory, file);
      const stats = await fs.stat(filePath);
      totalSize += stats.size;
      fileStats.push({
        file: filePath,
        size: stats.size,
        mtime: stats.mtime
      });
    }

    if (totalSize > this.options.maxSize) {
      // Sort by modification time (oldest first)
      fileStats.sort((a, b) => a.mtime.getTime() - b.mtime.getTime());
      
      // Remove oldest files until under limit
      for (const stat of fileStats) {
        if (totalSize <= this.options.maxSize) break;
        await fs.remove(stat.file);
        totalSize -= stat.size;
      }
    }
  }
}