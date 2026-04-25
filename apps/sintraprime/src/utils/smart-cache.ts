import { watch } from 'fs';
import { promises as fs } from 'fs';

export class SmartCache<T> {
  private cache = new Map<string, { data: T; mtime: number }>();
  private watchers = new Map<string, ReturnType<typeof watch>>();
  
  async get(
    key: string, 
    loader: () => Promise<T>,
    options: { watchFile?: boolean } = {}
  ): Promise<T> {
    try {
      const stat = await fs.stat(key);
      const cached = this.cache.get(key);
      
      if (cached && cached.mtime === stat.mtimeMs) {
        return cached.data;
      }
      
      const data = await loader();
      this.cache.set(key, { data, mtime: stat.mtimeMs });
      
      if (options.watchFile && !this.watchers.has(key)) {
        this.watchFile(key);
      }
      
      return data;
    } catch (err) {
      // If file doesn't exist, just call loader
      return loader();
    }
  }
  
  private watchFile(filePath: string) {
    const watcher = watch(filePath, (event) => {
      if (event === 'change' || event === 'rename') {
        this.cache.delete(filePath);
      }
    });
    this.watchers.set(filePath, watcher);
  }
  
  clear() {
    this.cache.clear();
    this.watchers.forEach(w => w.close());
    this.watchers.clear();
  }
  
  delete(key: string) {
    this.cache.delete(key);
    const watcher = this.watchers.get(key);
    if (watcher) {
      watcher.close();
      this.watchers.delete(key);
    }
  }
}

export const globalCache = new SmartCache();
