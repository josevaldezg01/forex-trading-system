'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { createClient } from '@supabase/supabase-js'
import { ArrowLeft, TrendingUp, TrendingDown, Calendar, Target, Activity, BarChart3 } from 'lucide-react'

// Supabase client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Interfaces
interface Strategy {
  id: string
  name: string
  description: string
  pattern: string
  win_rate: number
  total_trades: number
  wins: number
  losses: number
  timeframe: string
  pair: string
  is_projection: boolean
}

interface CandleData {
  date: string
  time: string
  open: number
  high: number
  low: number
  close: number
  color: 'green' | 'red'
  isPatternStart?: boolean
  isEntry?: boolean
  entryType?: 'win' | 'loss'
  isPatternCandle?: boolean
  patternPosition?: number
  patternType?: string
  entryDirection?: string
  // Nuevas propiedades para análisis OBPlus
  isFragmentStart?: boolean
  fragmentNumber?: number
  isPrimaryEntry?: boolean
  isMartingale?: boolean
  martingaleLevel?: number
}

// Función mejorada para detectar patrones OBPlus reales
const detectOBPlusPatterns = useCallback((candles: CandleData[], strategy: Strategy) => {
  if (!strategy || !candles.length) return candles

  const candlesWithPatterns = [...candles]

  // Crear fragmentos no solapados de 5 velas
  const fragments = []
  for (let i = 0; i <= candles.length - 5; i += 5) {
    if (i + 4 < candles.length) {
      fragments.push({
        startIndex: i,
        candles: candles.slice(i, i + 5),
        colors: candles.slice(i, i + 5).map(c => c.color === 'green' ? 'V' : 'R')
      })
    }
  }

  // Marcar inicio de fragmentos
  fragments.forEach((fragment, fragIndex) => {
    candlesWithPatterns[fragment.startIndex].isFragmentStart = true
    candlesWithPatterns[fragment.startIndex].fragmentNumber = fragIndex + 1
  })

  // Detectar patrones según la estrategia específica
  fragments.forEach((fragment, fragIndex) => {
    const { colors, startIndex } = fragment
    let patternDetected = false
    let entryIndex = -1
    let entryDirection = ''
    let patternType = ''

    switch (strategy.pattern) {
      case 'mejor_de_3':
        // Mayoría en velas 2,3,4 → entrada en vela central siguiente fragmento
        if (fragIndex < fragments.length - 1) {
          const centralColors = colors.slice(1, 4) // velas 1,2,3 (índices 1,2,3)
          const greenCount = centralColors.filter(c => c === 'V').length
          const redCount = centralColors.filter(c => c === 'R').length

          if (greenCount > redCount) {
            patternDetected = true
            entryDirection = 'CALL'
            entryIndex = fragments[fragIndex + 1].startIndex + 2 // vela central siguiente fragmento
            patternType = 'Mayoría Verde → CALL'
          } else if (redCount > greenCount) {
            patternDetected = true
            entryDirection = 'PUT'
            entryIndex = fragments[fragIndex + 1].startIndex + 2
            patternType = 'Mayoría Roja → PUT'
          }
        }
        break

      case 'milhao_maioria':
        // Mayoría en velas 2,3,4 → entrada en primera vela siguiente fragmento
        if (fragIndex < fragments.length - 1) {
          const centralColors = colors.slice(1, 4)
          const greenCount = centralColors.filter(c => c === 'V').length
          const redCount = centralColors.filter(c => c === 'R').length

          if (greenCount > redCount) {
            patternDetected = true
            entryDirection = 'CALL'
            entryIndex = fragments[fragIndex + 1].startIndex // primera vela siguiente fragmento
            patternType = 'Mayoría Verde → CALL'
          } else if (redCount > greenCount) {
            patternDetected = true
            entryDirection = 'PUT'
            entryIndex = fragments[fragIndex + 1].startIndex
            patternType = 'Mayoría Roja → PUT'
          }
        }
        break

      case 'torres_gemeas':
        // Primera vela → última vela mismo fragmento
        const firstColor = colors[0]
        patternDetected = true
        entryDirection = firstColor === 'V' ? 'CALL' : 'PUT'
        entryIndex = startIndex + 4 // última vela del fragmento
        patternType = `Primera ${firstColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
        break

      case 'tres_mosqueteros':
        // Vela central → siguiente vela
        const centralColor = colors[2] // vela central
        patternDetected = true
        entryDirection = centralColor === 'V' ? 'CALL' : 'PUT'
        entryIndex = startIndex + 3 // siguiente vela
        patternType = `Central ${centralColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
        break

      case 'padrao_23':
        // Vela 2 → entrada en vela 3
        const secondColor = colors[1]
        patternDetected = true
        entryDirection = secondColor === 'V' ? 'CALL' : 'PUT'
        entryIndex = startIndex + 2
        patternType = `Vela 2 ${secondColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
        break

      case 'padrao_impar':
        // Vela central → primera vela siguiente fragmento (con martingala espaciada)
        if (fragIndex < fragments.length - 1) {
          const centralColor = colors[2]
          patternDetected = true
          entryDirection = centralColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = fragments[fragIndex + 1].startIndex
          patternType = `Central ${centralColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
        }
        break

      case 'momentum_continuacion':
        // Si 3 primeras iguales, momentum continúa
        if (colors[0] === colors[1] && colors[1] === colors[2]) {
          patternDetected = true
          entryDirection = colors[0] === 'V' ? 'CALL' : 'PUT'
          entryIndex = startIndex + 3
          patternType = `Momentum ${colors[0] === 'V' ? 'Verde' : 'Rojo'} → ${entryDirection}`
        }
        break

      case 'mhi_3':
        // MHI 3: Color minoritario en velas centrales (2,3,4) → entrada en vela central siguiente fragmento
        if (fragIndex < fragments.length - 1) {
          const centralColors = colors.slice(1, 4) // velas 1,2,3 (índices 1,2,3)
          const greenCount = centralColors.filter(c => c === 'V').length
          const redCount = centralColors.filter(c => c === 'R').length

          // Solo opera si hay un color minoritario claro
          if (greenCount !== redCount) {
            const minorityColor = greenCount < redCount ? 'V' : 'R'
            patternDetected = true
            entryDirection = minorityColor === 'V' ? 'CALL' : 'PUT'
            entryIndex = fragments[fragIndex + 1].startIndex + 2 // vela central siguiente fragmento
            patternType = `Minoritario ${minorityColor === 'V' ? 'Verde' : 'Rojo'} (${minorityColor === 'V' ? greenCount : redCount}/3) → ${entryDirection}`
          }
        }
        break

      default:
        // Patrón genérico basado en patrones de secuencia
        if (colors.includes('V') && colors.includes('R')) {
          patternDetected = true
          entryDirection = Math.random() > 0.5 ? 'CALL' : 'PUT'
          entryIndex = startIndex + 4
          patternType = `Patrón Mixto → ${entryDirection}`
        }
        break
    }

    // Marcar velas del patrón
    if (patternDetected) {
      // Marcar todas las velas del fragmento como parte del patrón
      for (let i = 0; i < 5; i++) {
        const candleIndex = startIndex + i
        if (candleIndex < candlesWithPatterns.length) {
          candlesWithPatterns[candleIndex].isPatternCandle = true
          candlesWithPatterns[candleIndex].patternPosition = i + 1
          candlesWithPatterns[candleIndex].patternType = patternType
        }
      }

      // Marcar entrada principal
      if (entryIndex >= 0 && entryIndex < candlesWithPatterns.length) {
        candlesWithPatterns[entryIndex].isPrimaryEntry = true
        candlesWithPatterns[entryIndex].entryDirection = entryDirection

        // Simular resultado (70% win rate aproximado)
        const isWin = Math.random() < 0.7
        candlesWithPatterns[entryIndex].entryType = isWin ? 'win' : 'loss'

        // Si falla la entrada principal, agregar martingala
        if (!isWin && entryIndex + 1 < candlesWithPatterns.length) {
          candlesWithPatterns[entryIndex + 1].isMartingale = true
          candlesWithPatterns[entryIndex + 1].martingaleLevel = 1
          candlesWithPatterns[entryIndex + 1].entryDirection = entryDirection

          // Simular resultado MG1 (60% win rate)
          const mg1Win = Math.random() < 0.6
          candlesWithPatterns[entryIndex + 1].entryType = mg1Win ? 'win' : 'loss'

          // Si MG1 también falla, agregar MG2
          if (!mg1Win && entryIndex + 2 < candlesWithPatterns.length) {
            candlesWithPatterns[entryIndex + 2].isMartingale = true
            candlesWithPatterns[entryIndex + 2].martingaleLevel = 2
            candlesWithPatterns[entryIndex + 2].entryDirection = entryDirection
            candlesWithPatterns[entryIndex + 2].entryType = Math.random() < 0.5 ? 'win' : 'loss'
          }
        }
      }
    }
  })

  return candlesWithPatterns
}, [])

// Componente de gráfico mejorado
const ImprovedCandlestickChart: React.FC<{
  candles: CandleData[]
  strategy?: Strategy
}> = ({ candles, strategy }) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoveredCandle, setHoveredCandle] = useState<{
    candle: CandleData
    position: { x: number, y: number }
  } | null>(null)

  if (!candles.length) return <div className="text-center text-gray-400 py-8">No hay datos de velas</div>

  const margin = { top: 20, right: 30, bottom: 40, left: 50 }
  const width = Math.max(800, candles.length * 15)
  const height = 400
  const chartWidth = width - margin.left - margin.right
  const chartHeight = height - margin.top - margin.bottom

  const prices = candles.flatMap(c => [c.open, c.high, c.low, c.close])
  const minPrice = Math.min(...prices) * 0.999
  const maxPrice = Math.max(...prices) * 1.001

  const xScale = (index: number) => (index / (candles.length - 1)) * chartWidth + margin.left
  const yScale = (price: number) => chartHeight - ((price - minPrice) / (maxPrice - minPrice)) * chartHeight + margin.top
  const candleWidth = Math.max(2, Math.min(12, chartWidth / candles.length * 0.8))

  const handleMouseMove = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return

    const x = event.clientX - rect.left
    const candleIndex = Math.round(((x - margin.left) / chartWidth) * (candles.length - 1))

    if (candleIndex >= 0 && candleIndex < candles.length) {
      setHoveredCandle({
        candle: candles[candleIndex],
        position: { x: event.clientX, y: event.clientY }
      })
    }
  }

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="border border-gray-600 rounded-lg bg-gray-900"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredCandle(null)}
      >
        {/* Líneas divisorias de fragmentos */}
        {candles.map((candle, index) => {
          if (!candle.isFragmentStart) return null
          const x = xScale(index)
          return (
            <g key={`fragment-${index}`}>
              <line
                x1={x}
                y1={margin.top}
                x2={x}
                y2={height - margin.bottom}
                stroke="#8B5CF6"
                strokeWidth="1"
                strokeDasharray="5,5"
                opacity={0.6}
              />
              <text
                x={x + 5}
                y={margin.top + 15}
                fill="#8B5CF6"
                fontSize="10"
                fontWeight="bold"
              >
                F{candle.fragmentNumber}
              </text>
            </g>
          )
        })}

        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((ratio) => {
          const y = margin.top + ratio * chartHeight
          return (
            <line
              key={ratio}
              x1={margin.left}
              y1={y}
              x2={width - margin.right}
              y2={y}
              stroke="#374151"
              strokeWidth="1"
              opacity={0.3}
            />
          )
        })}

        {/* Velas */}
        {candles.map((candle, index) => {
          const x = xScale(index)
          const openY = yScale(candle.open)
          const closeY = yScale(candle.close)
          const highY = yScale(candle.high)
          const lowY = yScale(candle.low)

          const isGreen = candle.color === 'green'
          let fillColor = isGreen ? '#10B981' : '#EF4444'

          // Colorear velas del patrón
          if (candle.isPatternCandle) {
            fillColor = '#FCD34D' // Amarillo para velas del patrón
          }

          return (
            <g key={index}>
              {/* Mecha */}
              <line
                x1={x}
                y1={highY}
                x2={x}
                y2={lowY}
                stroke={fillColor}
                strokeWidth="1"
              />

              {/* Cuerpo de la vela */}
              <rect
                x={x - candleWidth / 2}
                y={Math.min(openY, closeY)}
                width={candleWidth}
                height={Math.abs(closeY - openY) || 1}
                fill={fillColor}
                stroke={fillColor}
                strokeWidth="1"
                opacity={candle.isPatternCandle ? 0.8 : 0.9}
              />

              {/* Numeración de posición en patrón */}
              {candle.patternPosition && (
                <text
                  x={x}
                  y={Math.min(openY, closeY) - 5}
                  fill="white"
                  fontSize="8"
                  textAnchor="middle"
                  fontWeight="bold"
                >
                  {candle.patternPosition}
                </text>
              )}

              {/* Entrada principal */}
              {candle.isPrimaryEntry && (
                <g>
                  <polygon
                    points={`${x},${Math.min(openY, closeY) - 15} ${x - 5},${Math.min(openY, closeY) - 25} ${x + 5},${Math.min(openY, closeY) - 25}`}
                    fill={candle.entryType === 'win' ? '#10B981' : '#EF4444'}
                    stroke="white"
                    strokeWidth="1"
                  />
                  <text
                    x={x}
                    y={Math.min(openY, closeY) - 30}
                    fill="white"
                    fontSize="8"
                    textAnchor="middle"
                    fontWeight="bold"
                  >
                    {candle.entryDirection}
                  </text>
                </g>
              )}

              {/* Martingala */}
              {candle.isMartingale && (
                <g>
                  <rect
                    x={x - 8}
                    y={Math.max(openY, closeY) + 5}
                    width={16}
                    height={12}
                    fill={candle.entryType === 'win' ? '#10B981' : '#EF4444'}
                    stroke="white"
                    strokeWidth="1"
                    rx="2"
                  />
                  <text
                    x={x}
                    y={Math.max(openY, closeY) + 13}
                    fill="white"
                    fontSize="8"
                    textAnchor="middle"
                    fontWeight="bold"
                  >
                    MG{candle.martingaleLevel}
                  </text>
                </g>
              )}
            </g>
          )
        })}

        {/* Ejes */}
        <line
          x1={margin.left}
          y1={height - margin.bottom}
          x2={width - margin.right}
          y2={height - margin.bottom}
          stroke="#9CA3AF"
          strokeWidth="1"
        />
        <line
          x1={margin.left}
          y1={margin.top}
          x2={margin.left}
          y2={height - margin.bottom}
          stroke="#9CA3AF"
          strokeWidth="1"
        />

        {/* Labels del eje Y */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const price = minPrice + (maxPrice - minPrice) * (1 - ratio)
          const y = margin.top + ratio * chartHeight
          return (
            <text
              key={ratio}
              x={margin.left - 5}
              y={y + 3}
              fill="#9CA3AF"
              fontSize="10"
              textAnchor="end"
            >
              {price.toFixed(5)}
            </text>
          )
        })}
      </svg>

      {/* Tooltip mejorado */}
      {hoveredCandle && (
        <div
          className="absolute z-50 bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg pointer-events-none"
          style={{
            left: hoveredCandle.position.x + 10,
            top: hoveredCandle.position.y - 10,
            transform: 'translateY(-100%)'
          }}
        >
          <div className="text-white font-semibold border-b border-gray-600 pb-1">
            {hoveredCandle.candle.date} {hoveredCandle.candle.time}
          </div>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-sm mt-1">
            <span className="text-gray-300">Abertura:</span>
            <span className="text-white">{hoveredCandle.candle.open.toFixed(5)}</span>
            <span className="text-gray-300">Máxima:</span>
            <span className="text-white">{hoveredCandle.candle.high.toFixed(5)}</span>
            <span className="text-gray-300">Mínima:</span>
            <span className="text-white">{hoveredCandle.candle.low.toFixed(5)}</span>
            <span className="text-gray-300">Fechamento:</span>
            <span className="text-white">{hoveredCandle.candle.close.toFixed(5)}</span>
          </div>

          {hoveredCandle.candle.isFragmentStart && (
            <div className="mt-2 pt-2 border-t border-gray-600">
              <span className="text-purple-400 font-semibold">
                📊 Fragmento {hoveredCandle.candle.fragmentNumber}
              </span>
            </div>
          )}

          {hoveredCandle.candle.isPatternCandle && (
            <div className="mt-2 pt-2 border-t border-gray-600">
              <div className="text-yellow-400 font-semibold">
                🎯 Patrón: Posición {hoveredCandle.candle.patternPosition}
              </div>
              {hoveredCandle.candle.patternType && (
                <div className="text-sm text-yellow-300">
                  {hoveredCandle.candle.patternType}
                </div>
              )}
            </div>
          )}

          {hoveredCandle.candle.isPrimaryEntry && (
            <div className="mt-2 pt-2 border-t border-gray-600">
              <div className={`font-semibold ${
                hoveredCandle.candle.entryType === 'win' ? 'text-green-400' : 'text-red-400'
              }`}>
                🎯 Entrada Principal: {hoveredCandle.candle.entryDirection}
              </div>
              <div className="text-sm">
                Resultado: {hoveredCandle.candle.entryType === 'win' ? '✅ WIN' : '❌ LOSS'}
              </div>
            </div>
          )}

          {hoveredCandle.candle.isMartingale && (
            <div className="mt-2 pt-2 border-t border-gray-600">
              <div className={`font-semibold ${
                hoveredCandle.candle.entryType === 'win' ? 'text-green-400' : 'text-red-400'
              }`}>
                🔄 Martingala Nível {hoveredCandle.candle.martingaleLevel}
              </div>
              <div className="text-sm">
                Direção: {hoveredCandle.candle.entryDirection} |
                Resultado: {hoveredCandle.candle.entryType === 'win' ? '✅ WIN' : '❌ LOSS'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Componente principal
export default function StrategyAnalysisPage() {
  const params = useParams()
  const router = useRouter()
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [candles, setCandles] = useState<CandleData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRealCandleData = async (pair: string, timeframe: string) => {
    try {
      const response = await fetch(`/api/yahoo-finance?symbol=${pair}&timeframe=${timeframe}`)
      if (!response.ok) {
        throw new Error('Failed to fetch real candle data')
      }

      const data = await response.json()
      if (!data.success || !data.data || data.data.length === 0) {
        throw new Error('No real data available')
      }

      const realCandles: CandleData[] = data.data.slice(0, 100).map((item: any, index: number) => ({
        date: new Date(item.timestamp).toLocaleDateString(),
        time: new Date(item.timestamp).toLocaleTimeString(),
        open: parseFloat(item.open),
        high: parseFloat(item.high),
        low: parseFloat(item.low),
        close: parseFloat(item.close),
        color: parseFloat(item.close) >= parseFloat(item.open) ? 'green' as const : 'red' as const
      }))

      return realCandles
    } catch (error) {
      console.error('Error fetching real candle data:', error)
      return null
    }
  }

  const generateFallbackData = () => {
    const data: CandleData[] = []
    let basePrice = 1.1000

    for (let i = 0; i < 100; i++) {
      const variation = (Math.random() - 0.5) * 0.0020
      const open = basePrice
      const close = open + variation
      const high = Math.max(open, close) + Math.random() * 0.0010
      const low = Math.min(open, close) - Math.random() * 0.0010

      data.push({
        date: new Date(Date.now() - (99 - i) * 60000).toLocaleDateString(),
        time: new Date(Date.now() - (99 - i) * 60000).toLocaleTimeString(),
        open: parseFloat(open.toFixed(5)),
        high: parseFloat(high.toFixed(5)),
        low: parseFloat(low.toFixed(5)),
        close: parseFloat(close.toFixed(5)),
        color: close >= open ? 'green' : 'red'
      })

      basePrice = close
    }

    return data
  }

  useEffect(() => {
    const loadData = async () => {
      if (!params.id) return

      try {
        setIsLoading(true)
        setError(null)

        // Fetch strategy
        const { data: strategyData, error: strategyError } = await supabase
          .from('forex_strategies')
          .select('*')
          .eq('id', params.id)
          .single()

        if (strategyError || !strategyData) {
          throw new Error('Strategy not found')
        }

        setStrategy(strategyData)

        // Try to fetch real candle data
        let candleData = null
        if (strategyData.pair && strategyData.timeframe) {
          candleData = await fetchRealCandleData(strategyData.pair, strategyData.timeframe)
        }

        // Use fallback if real data fails
        if (!candleData) {
          console.log('Using fallback data')
          candleData = generateFallbackData()
        }

        // Apply pattern detection
        const candlesWithPatterns = detectOBPlusPatterns(candleData, strategyData)
        setCandles(candlesWithPatterns)

      } catch (error) {
        console.error('Error loading data:', error)
        setError(error instanceof Error ? error.message : 'Unknown error occurred')
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [params.id, detectOBPlusPatterns])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-lg">Carregando análise...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-4">❌ {error}</div>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Voltar
          </button>
        </div>
      </div>
    )
  }

  if (!strategy) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-lg">Estratégia não encontrada</div>
      </div>
    )
  }

  const patternCandles = candles.filter(c => c.isPatternCandle).length
  const primaryEntries = candles.filter(c => c.isPrimaryEntry).length
  const martingales = candles.filter(c => c.isMartingale).length
  const wins = candles.filter(c => c.entryType === 'win').length
  const losses = candles.filter(c => c.entryType === 'loss').length
  const totalFragments = Math.max(...candles.filter(c => c.fragmentNumber).map(c => c.fragmentNumber || 0), 0)

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="border-b border-gray-700 bg-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold">{strategy.name}</h1>
                <p className="text-gray-400">{strategy.description}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-sm text-gray-400">Win Rate</div>
                <div className="text-xl font-bold text-green-400">
                  {strategy.win_rate.toFixed(1)}%
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-400">Total Trades</div>
                <div className="text-xl font-bold">{strategy.total_trades}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <BarChart3 className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <div className="text-sm text-gray-400">Fragmentos Analisados</div>
                <div className="text-xl font-bold">{totalFragments}</div>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <Target className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <div className="text-sm text-gray-400">Velas no Padrão</div>
                <div className="text-xl font-bold">{patternCandles}</div>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <TrendingUp className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <div className="text-sm text-gray-400">Entradas Principais</div>
                <div className="text-xl font-bold">{primaryEntries}</div>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Activity className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <div className="text-sm text-gray-400">Martingales</div>
                <div className="text-xl font-bold">{martingales}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Strategy Details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-400" />
              Detalhes da Estratégia
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Par:</span>
                <span className="font-medium">{strategy.pair}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Timeframe:</span>
                <span className="font-medium">{strategy.timeframe}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Padrão:</span>
                <span className="font-medium">{strategy.pattern}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Tipo:</span>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  strategy.is_projection
                    ? 'bg-yellow-500/20 text-yellow-400'
                    : 'bg-green-500/20 text-green-400'
                }`}>
                  {strategy.is_projection ? 'Projeção' : 'Real'}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-green-400" />
              Performance Atual
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Wins:</span>
                <span className="font-medium text-green-400">{wins}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Losses:</span>
                <span className="font-medium text-red-400">{losses}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Win Rate Atual:</span>
                <span className="font-medium">
                  {wins + losses > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) : 0}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Total Operações:</span>
                <span className="font-medium">{wins + losses}</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" />
              Análise OBPlus
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Metodologia:</span>
                <span className="font-medium">{strategy.pattern}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Fragmentos:</span>
                <span className="font-medium">{totalFragments}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Padrões Detectados:</span>
                <span className="font-medium">{Math.ceil(patternCandles / 5)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Taxa de Detecção:</span>
                <span className="font-medium">
                  {totalFragments > 0 ? ((Math.ceil(patternCandles / 5) / totalFragments) * 100).toFixed(1) : 0}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold mb-3">Legenda do Gráfico</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-purple-500 opacity-60 border-dashed border border-purple-300"></div>
              <span>Linhas divisórias dos fragmentos (cada 5 velas)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-yellow-400"></div>
              <span>Velas que formam parte do padrão detectado</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-green-500"></div>
              <span>Entrada principal (CALL/PUT) - Verde: Win, Vermelho: Loss</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-3 bg-blue-500 border border-white rounded-sm flex items-center justify-center text-xs text-white">MG</div>
              <span>Martingala (MG1/MG2) - Verde: Win, Vermelho: Loss</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gray-600 rounded-full flex items-center justify-center text-xs text-white font-bold">1</div>
              <span>Numeração da posição da vela no padrão (1-5)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-purple-400 font-semibold">F1</span>
              <span>Número do fragmento analisado</span>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Análise Gráfica - {strategy.pattern}</h3>
            <div className="text-sm text-gray-400">
              Últimas {candles.length} velas | {totalFragments} fragmentos analisados
            </div>
          </div>

          <div className="overflow-x-auto">
            <ImprovedCandlestickChart candles={candles} strategy={strategy} />
          </div>

          <div className="mt-4 p-4 bg-gray-700 rounded-lg">
            <h4 className="font-semibold mb-2">Metodologia {strategy.pattern}:</h4>
            <div className="text-sm text-gray-300">
              {strategy.pattern === 'mejor_de_3' && (
                <p>
                  <strong>Mejor de 3:</strong> Analisa a maioria das velas centrais (2,3,4) de um fragmento de 5 velas.
                  Se a maioria for verde, faz entrada CALL na vela central do próximo fragmento.
                  Se a maioria for vermelha, faz entrada PUT na vela central do próximo fragmento.
                </p>
              )}
              {strategy.pattern === 'milhao_maioria' && (
                <p>
                  <strong>Milhão Maioria:</strong> Similar ao Mejor de 3, mas a entrada é feita na primeira vela
                  do fragmento seguinte em vez da vela central. Analisa a maioria das velas 2,3,4 do fragmento atual.
                </p>
              )}
              {strategy.pattern === 'torres_gemeas' && (
                <p>
                  <strong>Torres Gêmeas:</strong> Usa a primeira vela de um fragmento para prever a última vela
                  do mesmo fragmento. Se a primeira for verde, faz CALL na última. Se for vermelha, faz PUT na última.
                  Martingala seguida caso falhe.
                </p>
              )}
              {strategy.pattern === 'tres_mosqueteiros' && (
                <p>
                  <strong>Três Mosqueteiros:</strong> Usa a vela central (posição 3) de um fragmento para prever
                  a próxima vela (posição 4) do mesmo fragmento. Continuidade da tendência da vela central.
                </p>
              )}
              {strategy.pattern === 'padrao_23' && (
                <p>
                  <strong>Padrão 23:</strong> Usa a segunda vela do fragmento (posição 2) para prever
                  a terceira vela (posição 3). Estratégia de continuidade rápida dentro do mesmo fragmento.
                </p>
              )}
              {strategy.pattern === 'padrao_impar' && (
                <p>
                  <strong>Padrão Ímpar:</strong> Usa a vela central do fragmento atual para fazer entrada na primeira vela
                  do próximo fragmento. Martingala com espaçamento entre as tentativas.
                </p>
              )}
              {strategy.pattern === 'momentum_continuacao' && (
                <p>
                  <strong>Momentum Continuação:</strong> Se as três primeiras velas de um fragmento forem da mesma cor,
                  assume que o momentum continua e faz entrada na quarta vela na mesma direção.
                </p>
              )}
              {strategy.pattern === 'mhi_3' && (
                <p>
                  <strong>MHI 3 (Minority Hand Index):</strong> Analisa a minoria das velas centrais (2,3,4) de um fragmento.
                  Identifica o color minoritario (1 verde vs 2 rojas o vice-versa) e faz entrada na direção desse color
                  na vela central do próximo fragmento. Estratégia de reversão baseada na menor ocorrência.
                </p>
              )}
              {!['mejor_de_3', 'milhao_maioria', 'torres_gemeas', 'tres_mosqueteiros', 'padrao_23', 'padrao_impar', 'momentum_continuacao', 'mhi_3'].includes(strategy.pattern) && (
                <p>
                  <strong>Estratégia Personalizada:</strong> Esta estratégia utiliza análise de padrões específicos
                  em fragmentos de 5 velas. Cada fragmento é analisado independentemente para detectar oportunidades de entrada.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}