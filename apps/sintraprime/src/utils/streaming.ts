import { createReadStream } from 'fs';
import { createInterface } from 'readline';

export async function* streamJsonLines<T = any>(filePath: string): AsyncGenerator<T> {
  const fileStream = createReadStream(filePath);
  const rl = createInterface({ 
    input: fileStream, 
    crlfDelay: Infinity 
  });
  
  for await (const line of rl) {
    if (!line.trim()) continue;
    try {
      yield JSON.parse(line) as T;
    } catch (err) {
      console.warn(`Failed to parse line: ${line.substring(0, 50)}...`);
      continue;
    }
  }
}

export async function getLastNLines<T = any>(
  filePath: string, 
  n: number
): Promise<T[]> {
  const results: T[] = [];
  for await (const item of streamJsonLines<T>(filePath)) {
    results.push(item);
    if (results.length > n) {
      results.shift();
    }
  }
  return results;
}
