/** Compresse une image côté client (JPEG ~1280px max, qualité 0.72). */
export async function compressImage(file, { maxSide = 1280, quality = 0.72 } = {}) {
  if (!file || !file.type?.startsWith('image/')) return file
  if (file.size < 350_000) return file

  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const w = Math.round(bitmap.width * scale)
  const h = Math.round(bitmap.height * scale)
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  ctx.drawImage(bitmap, 0, 0, w, h)
  bitmap.close?.()

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
  if (!blob) return file
  const name = (file.name || 'photo.jpg').replace(/\.\w+$/, '.jpg')
  return new File([blob], name, { type: 'image/jpeg', lastModified: Date.now() })
}
