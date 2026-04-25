import { parentPort, workerData } from 'worker_threads';
import crypto from 'crypto';
import fs from 'fs';

async function verifyFileBatch(files: string[]) {
  const results = await Promise.all(
    files.map(async (file) => {
      try {
        const data = await fs.promises.readFile(file);
        const hash = crypto.createHash('sha256').update(data).digest('hex');
        return { file, hash, valid: true };
      } catch (err) {
        return { file, error: String(err), valid: false };
      }
    })
  );
  return results;
}

parentPort?.on('message', async (files: string[]) => {
  try {
    const results = await verifyFileBatch(files);
    parentPort?.postMessage(results);
  } catch (err) {
    parentPort?.postMessage({ error: String(err) });
  }
});
