// Share links carry the whole card in the URL fragment: JSON, deflated, base64url. The fragment never
// reaches a server, so a link works on a static host and keeps the item private to whoever holds it.

const PREFIX = '#card=';

export async function encodeShare(data: object): Promise<string> {
  const json = new Blob([JSON.stringify(data)]);
  const packed = await new Response(
    json.stream().pipeThrough(new CompressionStream('deflate-raw'))
  ).arrayBuffer();
  let binary = '';
  for (const byte of new Uint8Array(packed)) {
    binary += String.fromCharCode(byte);
  }
  return PREFIX + btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}

/** The data a share fragment carries, or undefined when the fragment is not one or is damaged. */
export async function decodeShare(hash: string): Promise<unknown> {
  if (!hash.startsWith(PREFIX)) {
    return undefined;
  }
  try {
    const binary = atob(hash.slice(PREFIX.length).replaceAll('-', '+').replaceAll('_', '/'));
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return JSON.parse(await new Response(stream).text()) as unknown;
  } catch {
    // A truncated or edited link is just not a card; the editor starts from its default instead.
    return undefined;
  }
}
