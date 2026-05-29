import { Client } from '@gradio/client';

export async function generateHunyuan(prompt: string, onStatus: (s: string) => void) {
  onStatus('Connecting to Hunyuan3D...');
  
  const client = await Client.connect("tencent/Hunyuan3D-2");
  
  onStatus('Generating 3D model... (30-120s)');
  
  const result = await client.predict("/text_to_3d", {
    text: prompt,
  });
  
  return result.data;
}
