import { copyFileSync, existsSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const src = join(root, 'node_modules', 'leaflet', 'dist', 'images')
const dest = join(root, 'public')

if (!existsSync(dest)) mkdirSync(dest, { recursive: true })

for (const file of ['marker-icon.png', 'marker-icon-2x.png', 'marker-shadow.png']) {
  copyFileSync(join(src, file), join(dest, file))
  console.log(`Copied ${file} → public/`)
}
