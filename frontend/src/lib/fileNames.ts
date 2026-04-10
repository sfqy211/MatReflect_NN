export type ParsedAssetName = {
  rawName: string
  extension: string
  materialName: string
  timestampRaw: string | null
  timestampDisplay: string | null
  timestampSortValue: number | null
  hasLegacyTimestamp: boolean
}

const NEW_TIMESTAMP_SUFFIX = /^(.*)_(\d{8})_(\d{6})$/i
const LEGACY_TIMESTAMP_SUFFIX = /^(.*)_(\d{1,2})_(\d{6})$/i

function splitExtension(fileName: string) {
  const lastDot = fileName.lastIndexOf('.')
  if (lastDot === -1) {
    return { stem: fileName, extension: '' }
  }
  return {
    stem: fileName.slice(0, lastDot),
    extension: fileName.slice(lastDot + 1).toLowerCase(),
  }
}

function stripKnownSuffixes(stem: string) {
  return stem
    .replace(/_fc1$/i, '')
    .replace(/\.fullbin$/i, '')
    .replace(/\.binary$/i, '')
}

function formatNewTimestamp(datePart: string, timePart: string) {
  return `${datePart.slice(0, 4)}-${datePart.slice(4, 6)}-${datePart.slice(6, 8)} ${timePart.slice(0, 2)}:${timePart.slice(2, 4)}:${timePart.slice(4, 6)}`
}

function formatLegacyTimestamp(dayPart: string, timePart: string) {
  const paddedDay = dayPart.padStart(2, '0')
  return `${paddedDay} ${timePart.slice(0, 2)}:${timePart.slice(2, 4)}:${timePart.slice(4, 6)}`
}

export function parseAssetName(fileName: string): ParsedAssetName {
  const { stem, extension } = splitExtension(fileName)
  const normalizedStem = stripKnownSuffixes(stem)

  const newMatch = normalizedStem.match(NEW_TIMESTAMP_SUFFIX)
  if (newMatch) {
    const [, materialName, datePart, timePart] = newMatch
    return {
      rawName: fileName,
      extension,
      materialName,
      timestampRaw: `${datePart}_${timePart}`,
      timestampDisplay: formatNewTimestamp(datePart, timePart),
      timestampSortValue: Number(`${datePart}${timePart}`),
      hasLegacyTimestamp: false,
    }
  }

  const legacyMatch = normalizedStem.match(LEGACY_TIMESTAMP_SUFFIX)
  if (legacyMatch) {
    const [, materialName, dayPart, timePart] = legacyMatch
    return {
      rawName: fileName,
      extension,
      materialName,
      timestampRaw: `${dayPart}_${timePart}`,
      timestampDisplay: formatLegacyTimestamp(dayPart, timePart),
      timestampSortValue: null,
      hasLegacyTimestamp: true,
    }
  }

  return {
    rawName: fileName,
    extension,
    materialName: normalizedStem,
    timestampRaw: null,
    timestampDisplay: null,
    timestampSortValue: null,
    hasLegacyTimestamp: false,
  }
}

export function normalizeMaterialName(fileName: string) {
  return parseAssetName(fileName).materialName
}

export function compareAssetNamesByMaterial(a: string, b: string) {
  const parsedA = parseAssetName(a)
  const parsedB = parseAssetName(b)
  return parsedA.materialName.localeCompare(parsedB.materialName, 'zh-CN', { numeric: true, sensitivity: 'base' })
}

export function compareAssetNamesByTimestampDesc(a: string, b: string) {
  const parsedA = parseAssetName(a)
  const parsedB = parseAssetName(b)
  if (parsedA.timestampSortValue !== null && parsedB.timestampSortValue !== null) {
    return parsedB.timestampSortValue - parsedA.timestampSortValue
  }
  if (parsedA.timestampSortValue !== null) {
    return -1
  }
  if (parsedB.timestampSortValue !== null) {
    return 1
  }
  return b.localeCompare(a, 'zh-CN', { numeric: true, sensitivity: 'base' })
}
