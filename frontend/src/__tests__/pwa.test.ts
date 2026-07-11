import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('PWA manifest', () => {
  it('exists and parses as valid JSON with required keys', () => {
    const manifestPath = path.resolve(__dirname, '../../public/manifest.webmanifest');
    const raw = fs.readFileSync(manifestPath, 'utf8');
    const json = JSON.parse(raw);
    expect(json.name).toBe('My-Kiot POS');
    expect(json.short_name).toBe('Kiot POS');
    expect(json.start_url).toBe('/');
    expect(Array.isArray(json.icons)).toBe(true);
    expect(json.icons.length).toBeGreaterThan(0);
    expect(json.icons[0].src).toBeTruthy();
  });

  it('icon.svg exists', () => {
    const iconPath = path.resolve(__dirname, '../../public/icon.svg');
    expect(fs.existsSync(iconPath)).toBe(true);
  });
});
