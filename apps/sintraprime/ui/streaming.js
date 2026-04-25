import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';

export async function* streamJsonLines(filePath) {
  const fileStream = createReadStream(filePath);
  const rl = createInterface({ 
    input: fileStream, 
    crlfDelay: Infinity 
  });
  
  for await (const line of rl) {
    if (!line.trim()) continue;
    try {
      yield JSON.parse(line);
    } catch (err) {
      console.warn(`Failed to parse line: ${line.substring(0, 50)}...`);
      continue;
    }
  }
}

export async function getLastNLines(filePath, n) {
  const results = [];
  for await (const item of streamJsonLines(filePath)) {
    results.push(item);
    if (results.length > n) {
      results.shift();
    }
  }
  return results;
}
