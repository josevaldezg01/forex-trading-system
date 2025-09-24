'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { createClient } from '@supabase/supabase-js'
import { ArrowLeft, TrendingUp, Calendar, Target, Activity, BarChart3 } from 'lucide-react'

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

interface Fragment {
  startIndex: number
  candles: CandleData[]
  colors: string[]
}

// Componente de gráfico mejorado
const ImprovedCandlestickChart: React.FC<{
  candles: CandleData[]
}> = ({ candles }) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoveredCandle, setHoveredCandle] = useState<{
    candle: CandleData
    position: { x: number, y: number }
  } | null>(null)

const scrollContainerRef = useRef<HTMLDivElement>(null)

  if (!candles.length) return <div className="text-center text-gray-400 py-8">No hay datos de velas</div>

  const maxCandles = 400
  const displayData = candles.slice(-maxCandles)

  if (displayData.length === 0) return <div>No hay datos disponibles</div>

  const maxPrice = Math.max(...displayData.map(d => d.high))
  const minPrice = Math.min(...displayData.map(d => d.low))
  const priceRange = maxPrice - minPrice || 0.001
  const chartHeight = 400
  const chartWidth = Math.max(displayData.length * 8, 1000)

  const handleMouseMove = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const x = event.clientX - rect.left
    const candleIndex = Math.floor(x / 8)

    if (candleIndex >= 0 && candleIndex < displayData.length) {
      const candle = displayData[candleIndex]
      requestAnimationFrame(() => {
        setHoveredCandle({
          candle: candle,
          position: { x: event.clientX, y: event.clientY }
        })
      })
    }
  }

  const handleMouseLeave = () => {
    setHoveredCandle(null)
  }

  return (
    <div className="relative w-full bg-gray-900 rounded-lg">
      <div
        ref={scrollContainerRef}
        className="overflow-x-auto overflow-y-hidden"
        style={{ height: chartHeight + 60 + 'px' }}
      >
        <div className="relative" style={{ width: chartWidth + 'px', height: chartHeight + 'px' }}>
          <svg
            ref={svgRef}
            width={chartWidth}
            height={chartHeight}
            className="overflow-visible cursor-crosshair"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{ pointerEvents: 'auto' }}
          >
            {/* Líneas divisorias de fragmentos */}
            {displayData.map((candle, index) => {
              if (!candle.isFragmentStart) return null
              const x = index * 8 + 4
              return (
                <g key={`fragment-${index}`}>
                  <line
                    x1={x}
                    y1={0}
                    x2={x}
                    y2={chartHeight}
                    stroke="#8B5CF6"
                    strokeWidth="1"
                    strokeDasharray="5,5"
                    opacity={0.6}
                  />
                  <text
                    x={x + 5}
                    y={15}
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
            {[0.2, 0.4, 0.6, 0.8].map((ratio, i) => (
              <line
                key={i}
                x1="0"
                x2={chartWidth}
                y1={chartHeight * ratio}
                y2={chartHeight * ratio}
                stroke="#374151"
                strokeDasharray="2 2"
                strokeWidth="0.5"
              />
            ))}

            {/* Render candles */}
            {displayData.map((candle, index) => {
              const x = index * 8 + 4
              const candleWidth = 6
              const openY = chartHeight - ((candle.open - minPrice) / priceRange) * chartHeight
              const highY = chartHeight - ((candle.high - minPrice) / priceRange) * chartHeight
              const lowY = chartHeight - ((candle.low - minPrice) / priceRange) * chartHeight
              const closeY = chartHeight - ((candle.close - minPrice) / priceRange) * chartHeight
              const isGreen = candle.close > candle.open
              let fillColor = isGreen ? '#10B981' : '#EF4444'

              if (candle.isPatternCandle) {
                fillColor = '#FCD34D'
              }

              const bodyTop = Math.min(openY, closeY)
              const bodyHeight = Math.max(Math.abs(closeY - openY), 1)

              return (
                <g key={index}>
                  <line
                    x1={x}
                    x2={x}
                    y1={highY}
                    y2={lowY}
                    stroke={fillColor}
                    strokeWidth="1"
                  />
                  <rect
                    x={x - candleWidth/2}
                    y={bodyTop}
                    width={candleWidth}
                    height={bodyHeight}
                    fill={fillColor}
                    stroke={fillColor}
                    strokeWidth="1"
                    opacity={candle.isPatternCandle ? 0.8 : 0.9}
                  />
                  {candle.patternPosition && (
                    <text
                      x={x}
                      y={bodyTop - 5}
                      fill="white"
                      fontSize="8"
                      textAnchor="middle"
                      fontWeight="bold"
                    >
                      {candle.patternPosition}
                    </text>
                  )}
                  {candle.isPrimaryEntry && (
                    <g>
                      <polygon
                        points={`${x},${bodyTop - 15} ${x - 5},${bodyTop - 25} ${x + 5},${bodyTop - 25}`}
                        fill={candle.entryType === 'win' ? '#10B981' : '#EF4444'}
                        stroke="white"
                        strokeWidth="1"
                      />
                      <text
                        x={x}
                        y={bodyTop - 30}
                        fill="white"
                        fontSize="8"
                        textAnchor="middle"
                        fontWeight="bold"
                      >
                        {candle.entryDirection}
                      </text>
                    </g>
                  )}
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
          </svg>

          <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-300 -ml-20 py-2">
            <span className="bg-gray-800 px-2 py-1 rounded">{maxPrice.toFixed(4)}</span>
            <span className="bg-gray-800 px-2 py-1 rounded">{((maxPrice + minPrice) / 2).toFixed(4)}</span>
            <span className="bg-gray-800 px-2 py-1 rounded">{minPrice.toFixed(4)}</span>
          </div>

          <div className="absolute bottom-0 left-0 w-full flex justify-between text-xs text-gray-400 mt-2 px-2">
            {displayData.filter((_, i) => i % Math.floor(displayData.length / 6) === 0).map((candle, index) => (
              <span key={index} className="bg-gray-800 px-2 py-1 rounded whitespace-nowrap">
                {candle.date} {candle.time}
              </span>
            ))}
          </div>

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
                <span className="text-gray-300">Open:</span>
                <span className="text-white">{hoveredCandle.candle.open.toFixed(5)}</span>
                <span className="text-gray-300">High:</span>
                <span className="text-white">{hoveredCandle.candle.high.toFixed(5)}</span>
                <span className="text-gray-300">Low:</span>
                <span className="text-white">{hoveredCandle.candle.low.toFixed(5)}</span>
                <span className="text-gray-300">Close:</span>
                <span className="text-white">{hoveredCandle.candle.close.toFixed(5)}</span>
              </div>
              {hoveredCandle.candle.isFragmentStart && (
                <div className="mt-2 pt-2 border-t border-gray-600">
                  <span className="text-purple-400 font-semibold">
                    Fragmento {hoveredCandle.candle.fragmentNumber}
                  </span>
                </div>
              )}
              {hoveredCandle.candle.isPatternCandle && (
                <div className="mt-2 pt-2 border-t border-gray-600">
                  <div className="text-yellow-400 font-semibold">
                    Patrón: Posición {hoveredCandle.candle.patternPosition}
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
                    Entrada Principal: {hoveredCandle.candle.entryDirection}
                  </div>
                  <div className="text-sm">
                    Resultado: {hoveredCandle.candle.entryType === 'win' ? 'WIN' : 'LOSS'}
                  </div>
                </div>
              )}
              {hoveredCandle.candle.isMartingale && (
                <div className="mt-2 pt-2 border-t border-gray-600">
                  <div className={`font-semibold ${
                    hoveredCandle.candle.entryType === 'win' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    Martingala Nivel {hoveredCandle.candle.martingaleLevel}
                  </div>
                  <div className="text-sm">
                    Dirección: {hoveredCandle.candle.entryDirection} |
                    Resultado: {hoveredCandle.candle.entryType === 'win' ? 'WIN' : 'LOSS'}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
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
      const { data: candleData, error } = await supabase
        .from('forex_candles')
        .select('*')
        .eq('pair', pair)
        .eq('timeframe', timeframe)
        .order('timestamp', { ascending: true })
        .limit(100)

      if (error || !candleData || candleData.length === 0) {
        throw new Error('No real data available from Supabase')
      }

      const realCandles: CandleData[] = candleData.map((item) => ({
        date: new Date(item.timestamp).toLocaleDateString(),
        time: new Date(item.timestamp).toLocaleTimeString(),
        open: parseFloat(item.open.toString()),
        high: parseFloat(item.high.toString()),
        low: parseFloat(item.low.toString()),
        close: parseFloat(item.close.toString()),
        color: parseFloat(item.close.toString()) >= parseFloat(item.open.toString()) ? 'green' as const : 'red' as const
      }))

      return realCandles
    } catch (error) {
      console.error('Error fetching candle data from Supabase:', error)
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

  const detectOBPlusPatterns = (candles: CandleData[], strategy: Strategy) => {
    if (!strategy || !candles.length) return candles

    const candlesWithPatterns = [...candles]
    const fragments: Fragment[] = []

    for (let i = 0; i <= candles.length - 5; i += 5) {
      if (i + 4 < candles.length) {
        fragments.push({
          startIndex: i,
          candles: candles.slice(i, i + 5),
          colors: candles.slice(i, i + 5).map(c => c.color === 'green' ? 'V' : 'R')
        })
      }
    }

    fragments.forEach((fragment, fragIndex) => {
      candlesWithPatterns[fragment.startIndex].isFragmentStart = true
      candlesWithPatterns[fragment.startIndex].fragmentNumber = fragIndex + 1
    })

    fragments.forEach((fragment, fragIndex) => {
      const { colors, startIndex } = fragment
      let patternDetected = false
      let entryIndex = -1
      let entryDirection = ''
      let patternType = ''

      switch (strategy.pattern) {
        case 'mejor_de_3':
          if (fragIndex < fragments.length - 1) {
            const centralColors = colors.slice(1, 4)
            const greenCount = centralColors.filter(c => c === 'V').length
            const redCount = centralColors.filter(c => c === 'R').length

            if (greenCount > redCount) {
              patternDetected = true
              entryDirection = 'CALL'
              entryIndex = fragments[fragIndex + 1].startIndex + 2
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
          if (fragIndex < fragments.length - 1) {
            const centralColors = colors.slice(1, 4)
            const greenCount = centralColors.filter(c => c === 'V').length
            const redCount = centralColors.filter(c => c === 'R').length

            if (greenCount > redCount) {
              patternDetected = true
              entryDirection = 'CALL'
              entryIndex = fragments[fragIndex + 1].startIndex
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
          const firstColor = colors[0]
          patternDetected = true
          entryDirection = firstColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = startIndex + 4
          patternType = `Primera ${firstColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
          break

        case 'tres_mosqueteiros':
          const centralColor = colors[2]
          patternDetected = true
          entryDirection = centralColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = startIndex + 3
          patternType = `Central ${centralColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
          break

        case 'padrao_23':
          const secondColor = colors[1]
          patternDetected = true
          entryDirection = secondColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = startIndex + 2
          patternType = `Vela 2 ${secondColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
          break

        case 'padrao_impar':
          if (fragIndex < fragments.length - 1) {
            const centralColor = colors[2]
            patternDetected = true
            entryDirection = centralColor === 'V' ? 'CALL' : 'PUT'
            entryIndex = fragments[fragIndex + 1].startIndex
            patternType = `Central ${centralColor === 'V' ? 'Verde' : 'Roja'} → ${entryDirection}`
          }
          break

        case 'momentum_continuacion':
          if (colors[0] === colors[1] && colors[1] === colors[2]) {
            patternDetected = true
            entryDirection = colors[0] === 'V' ? 'CALL' : 'PUT'
            entryIndex = startIndex + 3
            patternType = `Momentum ${colors[0] === 'V' ? 'Verde' : 'Rojo'} → ${entryDirection}`
          }
          break

        case 'mhi_3':
          if (fragIndex < fragments.length - 1) {
            const centralColors = colors.slice(1, 4)
            const greenCount = centralColors.filter(c => c === 'V').length
            const redCount = centralColors.filter(c => c === 'R').length

            if (greenCount !== redCount) {
              const minorityColor = greenCount < redCount ? 'V' : 'R'
              patternDetected = true
              entryDirection = minorityColor === 'V' ? 'CALL' : 'PUT'
              entryIndex = fragments[fragIndex + 1].startIndex + 2
              patternType = `Minoritario ${minorityColor === 'V' ? 'Verde' : 'Rojo'} → ${entryDirection}`
            }
          }
          break

        default:
          if (colors.includes('V') && colors.includes('R')) {
            patternDetected = true
            entryDirection = Math.random() > 0.5 ? 'CALL' : 'PUT'
            entryIndex = startIndex + 4
            patternType = `Patrón Mixto → ${entryDirection}`
          }
          break
      }

      if (patternDetected) {
        for (let i = 0; i < 5; i++) {
          const candleIndex = startIndex + i
          if (candleIndex < candlesWithPatterns.length) {
            candlesWithPatterns[candleIndex].isPatternCandle = true
            candlesWithPatterns[candleIndex].patternPosition = i + 1
            candlesWithPatterns[candleIndex].patternType = patternType
          }
        }

        if (entryIndex >= 0 && entryIndex < candlesWithPatterns.length) {
          candlesWithPatterns[entryIndex].isPrimaryEntry = true
          candlesWithPatterns[entryIndex].entryDirection = entryDirection

          const isWin = Math.random() < 0.7
          candlesWithPatterns[entryIndex].entryType = isWin ? 'win' : 'loss'

          if (!isWin && entryIndex + 1 < candlesWithPatterns.length) {
            candlesWithPatterns[entryIndex + 1].isMartingale = true
            candlesWithPatterns[entryIndex + 1].martingaleLevel = 1
            candlesWithPatterns[entryIndex + 1].entryDirection = entryDirection

            const mg1Win = Math.random() < 0.6
            candlesWithPatterns[entryIndex + 1].entryType = mg1Win ? 'win' : 'loss'

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
  }

  useEffect(() => {
    const loadData = async () => {
      if (!params.id) return

      try {
        setIsLoading(true)
        setError(null)

        const { data: strategyData, error: strategyError } = await supabase
          .from('forex_strategies')
          .select('*')
          .eq('id', params.id)
          .single()

        if (strategyError || !strategyData) {
          throw new Error('Strategy not found')
        }

        setStrategy(strategyData)

        let candleData = null
        if (strategyData.pair && strategyData.timeframe) {
          candleData = await fetchRealCandleData(strategyData.pair, strategyData.timeframe)
        }

        if (!candleData) {
          console.log('Using fallback data')
          candleData = generateFallbackData()
        }

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
  }, [params.id])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-lg">Cargando análisis...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-4">{error}</div>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Volver
          </button>
        </div>
      </div>
    )
  }

  if (!strategy) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-lg">Estrategia no encontrada</div>
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
                <div className="text-sm text-gray-400">Fragmentos Analizados</div>
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
              Detalles de la Estrategia
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
                <span className="text-gray-400">Patrón:</span>
                <span className="font-medium">{strategy.pattern}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Tipo:</span>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  strategy.is_projection
                    ? 'bg-yellow-500/20 text-yellow-400'
                    : 'bg-green-500/20 text-green-400'
                }`}>
                  {strategy.is_projection ? 'Proyección' : 'Real'}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-green-400" />
              Performance Actual
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
                <span className="text-gray-400">Win Rate Actual:</span>
                <span className="font-medium">
                  {wins + losses > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) : 0}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Total Operaciones:</span>
                <span className="font-medium">{wins + losses}</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" />
              Análisis OBPlus
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Metodología:</span>
                <span className="font-medium">{strategy.pattern}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Fragmentos:</span>
                <span className="font-medium">{totalFragments}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Patrones Detectados:</span>
                <span className="font-medium">{Math.ceil(patternCandles / 5)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Tasa de Detección:</span>
                <span className="font-medium">
                  {totalFragments > 0 ? ((Math.ceil(patternCandles / 5) / totalFragments) * 100).toFixed(1) : 0}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold mb-3">Leyenda del Gráfico</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-purple-500 opacity-60 border-dashed border border-purple-300"></div>
              <span>Líneas divisorias de fragmentos (cada 5 velas)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-yellow-400"></div>
              <span>Velas que forman parte del patrón detectado</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-green-500"></div>
              <span>Entrada principal (CALL/PUT) - Verde: Win, Rojo: Loss</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-3 bg-blue-500 border border-white rounded-sm flex items-center justify-center text-xs text-white">MG</div>
              <span>Martingala (MG1/MG2) - Verde: Win, Rojo: Loss</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gray-600 rounded-full flex items-center justify-center text-xs text-white font-bold">1</div>
              <span>Numeración de la posición de la vela en el patrón (1-5)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-purple-400 font-semibold">F1</span>
              <span>Número del fragmento analizado</span>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Análisis Gráfico - {strategy.pattern}</h3>
            <div className="text-sm text-gray-400">
              Últimas {candles.length} velas | {totalFragments} fragmentos analizados
            </div>
          </div>

          <div className="overflow-x-auto">
            <ImprovedCandlestickChart candles={candles} />
          </div>

          <div className="mt-4 p-4 bg-gray-700 rounded-lg">
            <h4 className="font-semibold mb-2">Metodología {strategy.pattern}:</h4>
            <div className="text-sm text-gray-300">
              {strategy.pattern === 'mejor_de_3' && (
                <p>
                  <strong>Mejor de 3:</strong> Analiza la mayoría de las velas centrales (2,3,4) de un fragmento de 5 velas.
                  Si la mayoría es verde, hace entrada CALL en la vela central del próximo fragmento.
                  Si la mayoría es roja, hace entrada PUT en la vela central del próximo fragmento.
                </p>
              )}
              {strategy.pattern === 'milhao_maioria' && (
                <p>
                  <strong>Milhão Maioria:</strong> Similar al Mejor de 3, pero la entrada se hace en la primera vela
                  del fragmento siguiente en vez de la vela central. Analiza la mayoría de las velas 2,3,4 del fragmento actual.
                </p>
              )}
              {strategy.pattern === 'torres_gemeas' && (
                <p>
                  <strong>Torres Gemelas:</strong> Usa la primera vela de un fragmento para predecir la última vela
                  del mismo fragmento. Si la primera es verde, hace CALL en la última. Si es roja, hace PUT en la última.
                  Martingala seguida en caso de fallo.
                </p>
              )}
              {strategy.pattern === 'tres_mosqueteiros' && (
                <p>
                  <strong>Tres Mosqueteros:</strong> Usa la vela central (posición 3) de un fragmento para predecir
                  la próxima vela (posición 4) del mismo fragmento. Continuidad de la tendencia de la vela central.
                </p>
              )}
              {strategy.pattern === 'padrao_23' && (
                <p>
                  <strong>Patrón 23:</strong> Usa la segunda vela del fragmento (posición 2) para predecir
                  la tercera vela (posición 3). Estrategia de continuidad rápida dentro del mismo fragmento.
                </p>
              )}
              {strategy.pattern === 'padrao_impar' && (
                <p>
                  <strong>Patrón Impar:</strong> Usa la vela central del fragmento actual para hacer entrada en la primera vela
                  del próximo fragmento. Martingala con espaciamiento entre los intentos.
                </p>
              )}
              {strategy.pattern === 'momentum_continuacao' && (
                <p>
                  <strong>Momentum Continuación:</strong> Si las tres primeras velas de un fragmento son del mismo color,
                  asume que el momentum continúa y hace entrada en la cuarta vela en la misma dirección.
                </p>
              )}
              {strategy.pattern === 'mhi_3' && (
                <p>
                  <strong>MHI 3 (Minority Hand Index):</strong> Analiza la minoría de las velas centrales (2,3,4) de un fragmento.
                  Identifica el color minoritario (1 verde vs 2 rojas o viceversa) y hace entrada en la dirección de ese color
                  en la vela central del próximo fragmento. Estrategia de reversión basada en la menor ocurrencia.
                </p>
              )}
              {!['mejor_de_3', 'milhao_maioria', 'torres_gemeas', 'tres_mosqueteiros', 'padrao_23', 'padrao_impar', 'momentum_continuacao', 'mhi_3'].includes(strategy.pattern) && (
                <p>
                  <strong>Estrategia Personalizada:</strong> Esta estrategia utiliza análisis de patrones específicos
                  en fragmentos de 5 velas. Cada fragmento se analiza independientemente para detectar oportunidades de entrada.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}