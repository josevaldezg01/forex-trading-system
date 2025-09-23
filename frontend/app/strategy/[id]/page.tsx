'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { createClient } from '@supabase/supabase-js'
import { ArrowLeft, TrendingUp, TrendingDown, Calendar, Target, BarChart3 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts'

// Configuración Supabase
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

interface Strategy {
  id: number
  pair: string
  timeframe: string
  pattern: string
  direction: string
  effectiveness: number
  occurrences: number
  wins: number
  losses: number
  avg_profit: number
  score: number
  analysis_date: string
  type?: string
  description?: string
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
  // NUEVAS PROPIEDADES para análisis OBPlus:
  isFragmentStart?: boolean
  fragmentNumber?: number
  isPrimaryEntry?: boolean
  isMartingale?: boolean
  martingaleLevel?: number
}

export default function StrategyDetail() {
  const params = useParams()
  const router = useRouter()
  const strategyId = params.id as string

  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [candleData, setCandleData] = useState<CandleData[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTimeRange, setSelectedTimeRange] = useState('1M')
  const [selectedCandleSize, setSelectedCandleSize] = useState('1h')
  const [hoveredCandle, setHoveredCandle] = useState<{candle: CandleData, x: number, y: number} | null>(null)

  const fetchStrategyDetail = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('forex_strategies')
        .select('*')
        .eq('id', parseInt(strategyId))
        .single()

      if (error) {
        console.error('Error fetching strategy:', error)
        return
      }

      setStrategy(data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }, [strategyId])

  // Función mejorada para detectar patrones OBPlus reales
  const detectOBPlusPatterns = useCallback((candles: CandleData[], strategy: Strategy) => {
    if (!strategy || !candles.length) return candles

    const candlesWithPatterns = [...candles]
    const pattern = strategy.pattern

    // Crear fragmentos de 5 velas NO solapados
    const fragments: Array<{
      startIndex: number
      candles: CandleData[]
      colors: string[]
    }> = []

    for (let i = 0; i <= candles.length - 5; i += 5) {
      const fragmentCandles = candles.slice(i, i + 5)
      if (fragmentCandles.length === 5) {
        const colors = fragmentCandles.map(c => c.close >= c.open ? 'V' : 'R')
        fragments.push({
          startIndex: i,
          candles: fragmentCandles,
          colors: colors
        })
      }
    }

    // Marcar líneas divisorias de fragmentos
    fragments.forEach((fragment, fragmentIndex) => {
      // Marcar inicio de fragmento
      if (fragment.startIndex < candlesWithPatterns.length) {
        candlesWithPatterns[fragment.startIndex] = {
          ...candlesWithPatterns[fragment.startIndex],
          isFragmentStart: true,
          fragmentNumber: fragmentIndex + 1
        }
      }
    })

    // Detectar patrones según la estrategia específica
    fragments.forEach((fragment, fragmentIndex) => {
      let patternDetected = false
      let predictedDirection: 'CALL' | 'PUT' | null = null
      let entryIndex: number | null = null

      switch (pattern) {
        case 'mejor_de_3':
          // Mayoría en velas 2,3,4 → entrada en vela central siguiente fragmento
          if (fragmentIndex < fragments.length - 1) {
            const centralColors = fragment.colors.slice(1, 4) // Velas 1,2,3 (índices 1,2,3)
            const counts = centralColors.reduce((acc, color) => {
              acc[color] = (acc[color] || 0) + 1
              return acc
            }, {} as Record<string, number>)

            const majorityColor = Object.keys(counts).reduce((a, b) =>
              counts[a] > counts[b] ? a : b
            )

            if (counts[majorityColor] >= 2) { // Al menos 2 de 3 iguales
              patternDetected = true
              predictedDirection = majorityColor === 'V' ? 'CALL' : 'PUT'
              entryIndex = fragments[fragmentIndex + 1].startIndex + 2 // Vela central siguiente fragmento
            }
          }
          break

        case 'milhao_maioria':
          // Mayoría en velas 2,3,4 → entrada en primera vela siguiente fragmento
          if (fragmentIndex < fragments.length - 1) {
            const centralColors = fragment.colors.slice(1, 4)
            const counts = centralColors.reduce((acc, color) => {
              acc[color] = (acc[color] || 0) + 1
              return acc
            }, {} as Record<string, number>)

            const majorityColor = Object.keys(counts).reduce((a, b) =>
              counts[a] > counts[b] ? a : b
            )

            if (counts[majorityColor] >= 2) {
              patternDetected = true
              predictedDirection = majorityColor === 'V' ? 'CALL' : 'PUT'
              entryIndex = fragments[fragmentIndex + 1].startIndex // Primera vela siguiente fragmento
            }
          }
          break

        case 'tres_mosqueteros':
          // Vela central → siguiente vela (mismo fragmento)
          const centralColor = fragment.colors[2] // Vela central (índice 2)
          patternDetected = true
          predictedDirection = centralColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = fragment.startIndex + 3 // Siguiente vela (índice 3)
          break

        case 'torres_gemeas':
          // Primera vela → última vela mismo fragmento
          const firstColor = fragment.colors[0]
          patternDetected = true
          predictedDirection = firstColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = fragment.startIndex + 4 // Última vela (índice 4)
          break

        case 'padrao_23':
          // Vela patrón (pos 2) → entrada en pos 3
          const patternColor = fragment.colors[1] // Posición 2 (índice 1)
          patternDetected = true
          predictedDirection = patternColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = fragment.startIndex + 2 // Posición 3 (índice 2)
          break

        case 'padrao_impar':
          // Vela central → primera vela siguiente fragmento
          if (fragmentIndex < fragments.length - 1) {
            const centralColor = fragment.colors[2]
            patternDetected = true
            predictedDirection = centralColor === 'V' ? 'CALL' : 'PUT'
            entryIndex = fragments[fragmentIndex + 1].startIndex
          }
          break

        case 'momentum_continuacion':
          // Si las 3 primeras velas son iguales → entrada en primera vela siguiente fragmento
          if (fragmentIndex < fragments.length - 1) {
            const firstThree = fragment.colors.slice(0, 3)
            const allSame = firstThree.every(color => color === firstThree[0])

            if (allSame) {
              patternDetected = true
              predictedDirection = firstThree[0] === 'V' ? 'CALL' : 'PUT'
              entryIndex = fragments[fragmentIndex + 1].startIndex
            }
          }
          break

        case 'mhi_3':
          // Color minoritario → entrada específica
          if (fragmentIndex < fragments.length - 1) {
            const centralColors = fragment.colors.slice(1, 4)
            const counts = centralColors.reduce((acc, color) => {
              acc[color] = (acc[color] || 0) + 1
              return acc
            }, {} as Record<string, number>)

            if (Object.keys(counts).length > 1) { // Hay colores diferentes
              const minorityColor = Object.keys(counts).reduce((a, b) =>
                counts[a] < counts[b] ? a : b
              )

              patternDetected = true
              predictedDirection = minorityColor === 'V' ? 'CALL' : 'PUT'
              entryIndex = fragments[fragmentIndex + 1].startIndex + 2 // Vela central siguiente
            }
          }
          break

        case 'extremos_opuestos':
          // Primera vela opuesta a última vela mismo fragmento
          const firstColorEO = fragment.colors[0]
          const predictedOpposite = firstColorEO === 'V' ? 'R' : 'V'
          patternDetected = true
          predictedDirection = predictedOpposite === 'V' ? 'CALL' : 'PUT'
          entryIndex = fragment.startIndex + 4 // Última vela
          break

        case 'simetria_central':
          // Vela 2 similar a vela 4
          const secondColor = fragment.colors[1]
          patternDetected = true
          predictedDirection = secondColor === 'V' ? 'CALL' : 'PUT'
          entryIndex = fragment.startIndex + 3 // Vela 4 (índice 3)
          break
      }

      if (patternDetected && entryIndex !== null && entryIndex < candlesWithPatterns.length) {
        // Marcar velas del patrón
        fragment.candles.forEach((_, candleIndex) => {
          const globalIndex = fragment.startIndex + candleIndex
          if (globalIndex < candlesWithPatterns.length) {
            candlesWithPatterns[globalIndex] = {
              ...candlesWithPatterns[globalIndex],
              isPatternCandle: true,
              patternPosition: candleIndex,
              patternType: fragment.colors[candleIndex],
              isPatternStart: candleIndex === 0,
              fragmentNumber: fragmentIndex + 1
            }
          }
        })

        // Determinar si la entrada fue correcta
        const entryCandle = candlesWithPatterns[entryIndex]
        const actualDirection: 'CALL' | 'PUT' = entryCandle.close >= entryCandle.open ? 'CALL' : 'PUT'
        const isWin = predictedDirection === actualDirection

        // Marcar la entrada principal
        candlesWithPatterns[entryIndex] = {
          ...candlesWithPatterns[entryIndex],
          isEntry: true,
          entryType: isWin ? 'win' : 'loss',
          entryDirection: predictedDirection,
          isPrimaryEntry: true,
          martingaleLevel: 0
        }

        // Simular martingala si la primera entrada fue pérdida
        if (!isWin && entryIndex + 1 < candlesWithPatterns.length) {
          // MG1 - Segunda oportunidad
          const mg1Index = entryIndex + 1
          const mg1Candle = candlesWithPatterns[mg1Index]
          const mg1ActualDirection: 'CALL' | 'PUT' = mg1Candle.close >= mg1Candle.open ? 'CALL' : 'PUT'
          const mg1IsWin = predictedDirection === mg1ActualDirection

          candlesWithPatterns[mg1Index] = {
            ...candlesWithPatterns[mg1Index],
            isEntry: true,
            entryType: mg1IsWin ? 'win' : 'loss',
            entryDirection: predictedDirection,
            isMartingale: true,
            martingaleLevel: 1
          }

          // Si MG1 también falló, intentar MG2
          if (!mg1IsWin && entryIndex + 2 < candlesWithPatterns.length) {
            const mg2Index = entryIndex + 2
            const mg2Candle = candlesWithPatterns[mg2Index]
            const mg2ActualDirection: 'CALL' | 'PUT' = mg2Candle.close >= mg2Candle.open ? 'CALL' : 'PUT'
            const mg2IsWin = predictedDirection === mg2ActualDirection

            candlesWithPatterns[mg2Index] = {
              ...candlesWithPatterns[mg2Index],
              isEntry: true,
              entryType: mg2IsWin ? 'win' : 'loss',
              entryDirection: predictedDirection,
              isMartingale: true,
              martingaleLevel: 2
            }
          }
        }
      }
    })

    return candlesWithPatterns
  }, [])

  // Datos simulados como fallback
  const generateFallbackData = useCallback(() => {
    const data: CandleData[] = []
    const basePrice = 1.0850
    let currentPrice = basePrice

    for (let i = 0; i < 100; i++) {
      const date = new Date(Date.now() - (100 - i) * 60 * 60 * 1000)
      const open = currentPrice
      const change = (Math.random() - 0.5) * 0.004
      const close = open + change
      const high = Math.max(open, close) + Math.random() * 0.002
      const low = Math.min(open, close) - Math.random() * 0.002

      data.push({
        date: date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' }),
        time: date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
        open: parseFloat(open.toFixed(5)),
        high: parseFloat(high.toFixed(5)),
        low: parseFloat(low.toFixed(5)),
        close: parseFloat(close.toFixed(5)),
        color: close > open ? 'green' : 'red',
        isPatternStart: Math.random() < 0.05,
        isEntry: Math.random() < 0.02,
        entryType: Math.random() < 0.95 ? 'win' : 'loss'
      })

      currentPrice = close
    }

    const candlesWithPatterns = strategy ? detectOBPlusPatterns(data, strategy) : data
    setCandleData(candlesWithPatterns)
    console.log('Usando datos simulados como fallback')
  }, [strategy, detectOBPlusPatterns])

  // Cargar datos reales de Supabase
  const fetchRealCandleData = useCallback(async () => {
    if (!strategy) return

    try {
      setLoading(true)

      const pair = strategy.pair.replace('/', '')
      const availableTimeframes = ['1h', '1d', '1w', '1M']
      const actualTimeframe = availableTimeframes.includes(selectedCandleSize) ? selectedCandleSize : '1h'

      const endDate = new Date()
      const startDate = new Date()

      switch (selectedTimeRange) {
        case '1W': startDate.setDate(endDate.getDate() - 7); break
        case '1M': startDate.setMonth(endDate.getMonth() - 1); break
        case '3M': startDate.setMonth(endDate.getMonth() - 3); break
        case '6M': startDate.setMonth(endDate.getMonth() - 6); break
        case '1Y': startDate.setFullYear(endDate.getFullYear() - 1); break
        default: startDate.setMonth(endDate.getMonth() - 1)
      }

      const { data, error } = await supabase
        .from('forex_candles')
        .select('*')
        .eq('pair', pair)
        .eq('timeframe', actualTimeframe)
        .gte('datetime', startDate.toISOString())
        .lte('datetime', endDate.toISOString())
        .order('datetime', { ascending: true })
        .limit(2000)

      if (error) {
        console.error('Error fetching candle data:', error)
        generateFallbackData()
        return
      }

      if (!data || data.length === 0) {
        console.warn(`No hay datos para ${pair} ${actualTimeframe} en el rango seleccionado`)
        generateFallbackData()
        return
      }

      const realCandles: CandleData[] = data.map((candle) => {
        const candleDate = new Date(candle.datetime)
        const isGreen = candle.close > candle.open

        return {
          date: candleDate.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' }),
          time: candleDate.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
          open: parseFloat(candle.open.toFixed(5)),
          high: parseFloat(candle.high.toFixed(5)),
          low: parseFloat(candle.low.toFixed(5)),
          close: parseFloat(candle.close.toFixed(5)),
          color: isGreen ? 'green' : 'red'
        }
      })

      const candlesWithPatterns = detectOBPlusPatterns(realCandles, strategy)
      setCandleData(candlesWithPatterns)
      console.log(`Cargados ${candlesWithPatterns.length} datos reales para ${pair} ${actualTimeframe}`)

    } catch (error) {
      console.error('Error fetching real data:', error)
      generateFallbackData()
    } finally {
      setLoading(false)
    }
  }, [strategy, selectedTimeRange, selectedCandleSize, detectOBPlusPatterns, generateFallbackData])

  useEffect(() => {
    if (strategyId) {
      fetchStrategyDetail()
    }
  }, [strategyId, fetchStrategyDetail])

  useEffect(() => {
    fetchRealCandleData()
  }, [fetchRealCandleData])

  const getDirectionIcon = (direction: string) => {
    return direction === 'CALL' ?
      <TrendingUp className="w-5 h-5 text-green-600" /> :
      <TrendingDown className="w-5 h-5 text-red-600" />
  }

  const getEffectivenessColor = (effectiveness: number) => {
    if (effectiveness >= 90) return 'text-green-600'
    if (effectiveness >= 80) return 'text-green-500'
    if (effectiveness >= 70) return 'text-yellow-600'
    return 'text-red-500'
  }

  // Componente de gráfico mejorado con análisis OBPlus
  const ImprovedCandlestickChart = ({ data }: { data: Array<{
    index: number
    price: number
    open: number
    high: number
    low: number
    close: number
    date: string
    time: string
    isEntry?: boolean
    entryType?: 'win' | 'loss'
    isPatternStart?: boolean
    isPatternCandle?: boolean
    patternType?: string
    patternPosition?: number
    entryDirection?: string
    isFragmentStart?: boolean
    fragmentNumber?: number
    isPrimaryEntry?: boolean
    isMartingale?: boolean
    martingaleLevel?: number
  }> }) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null)

    if (data.length === 0) return <div>No hay datos disponibles</div>

    const maxPrice = Math.max(...data.map(d => d.high || d.price))
    const minPrice = Math.min(...data.map(d => d.low || d.price))
    const priceRange = maxPrice - minPrice || 0.001
    const chartHeight = 450
    const chartWidth = Math.max(data.length * 12, 1200)

    const handleMouseMove = (event: React.MouseEvent<SVGSVGElement>) => {
      const rect = event.currentTarget.getBoundingClientRect()
      const x = event.clientX - rect.left
      const candleIndex = Math.floor(x / 12)

      if (candleIndex >= 0 && candleIndex < data.length) {
        const candle = data[candleIndex]
        setHoveredCandle({
          candle: candle as any,
          x: x,
          y: event.clientY - rect.top
        })
      }
    }

    return (
      <div className="relative w-full bg-gray-900 rounded-lg">
        <div
          ref={scrollContainerRef}
          className="overflow-x-auto overflow-y-hidden"
          style={{ height: chartHeight + 80 + 'px' }}
        >
          <div className="relative" style={{ width: chartWidth + 'px', height: chartHeight + 'px' }}>
            <svg
              width={chartWidth}
              height={chartHeight}
              className="overflow-visible cursor-crosshair"
              onMouseMove={handleMouseMove}
              onMouseLeave={() => setHoveredCandle(null)}
            >
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

              {/* Líneas divisorias de fragmentos cada 5 velas */}
              {data.filter(candle => candle.isFragmentStart).map((candle) => (
                <g key={`fragment-${candle.index}`}>
                  <line
                    x1={candle.index * 12 + 6}
                    x2={candle.index * 12 + 6}
                    y1="0"
                    y2={chartHeight}
                    stroke="#8B5CF6"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                  />
                  <text
                    x={candle.index * 12 + 30}
                    y={15}
                    fill="#8B5CF6"
                    fontSize="11"
                    className="font-bold"
                  >
                    Fragmento #{candle.fragmentNumber}
                  </text>
                </g>
              ))}

              {/* Render candles */}
              {data.map((candle, index) => {
                const x = index * 12 + 6
                const candleWidth = 8

                const open = candle.open || candle.price
                const high = candle.high || candle.price
                const low = candle.low || candle.price
                const close = candle.close || candle.price

                const openY = chartHeight - ((open - minPrice) / priceRange) * chartHeight
                const highY = chartHeight - ((high - minPrice) / priceRange) * chartHeight
                const lowY = chartHeight - ((low - minPrice) / priceRange) * chartHeight
                const closeY = chartHeight - ((close - minPrice) / priceRange) * chartHeight

                const isGreen = close > open
                const bodyTop = Math.min(openY, closeY)
                const bodyHeight = Math.max(Math.abs(closeY - openY), 1)

                return (
                  <g key={index}>
                    {/* Hover area */}
                    <rect
                      x={x - 6}
                      y={0}
                      width={12}
                      height={chartHeight}
                      fill="transparent"
                      className="hover:fill-white hover:fill-opacity-5"
                    />

                    {/* Candle wick */}
                    <line
                      x1={x}
                      x2={x}
                      y1={highY}
                      y2={lowY}
                      stroke={isGreen ? '#10B981' : '#EF4444'}
                      strokeWidth="1"
                    />

                    {/* Candle body */}
                    <rect
                      x={x - candleWidth/2}
                      y={bodyTop}
                      width={candleWidth}
                      height={bodyHeight}
                      fill={candle.isPatternCandle ? '#FCD34D' : (isGreen ? '#10B981' : '#EF4444')}
                      stroke={candle.isPatternCandle ? '#F59E0B' : (isGreen ? '#10B981' : '#EF4444')}
                      strokeWidth={candle.isPatternCandle ? 2 : 1}
                      opacity="0.9"
                    />

                    {/* Marcadores de patrón */}
                    {candle.isPatternCandle && (
                      <g>
                        <circle
                          cx={x}
                          cy={chartHeight - 30}
                          r="8"
                          fill="#fbbf24"
                          stroke="#f59e0b"
                          strokeWidth="2"
                        />
                        <text
                          x={x}
                          y={chartHeight - 26}
                          textAnchor="middle"
                          fontSize="10"
                          fill="#000"
                          className="font-bold"
                        >
                          {(candle.patternPosition || 0) + 1}
                        </text>
                      </g>
                    )}

                    {/* Marcadores de entrada */}
                    {candle.isEntry && (
                      <g>
                        {/* Entrada principal */}
                        {candle.isPrimaryEntry && (
                          <>
                            <polygon
                              points={`${x-10},40 ${x+10},40 ${x},20`}
                              fill={candle.entryType === 'win' ? '#10b981' : '#ef4444'}
                              stroke={candle.entryType === 'win' ? '#059669' : '#dc2626'}
                              strokeWidth="2"
                            />
                            <text
                              x={x}
                              y={15}
                              textAnchor="middle"
                              fontSize="9"
                              fill={candle.entryType === 'win' ? '#10b981' : '#ef4444'}
                              className="font-bold"
                            >
                              ENTRADA
                            </text>
                          </>
                        )}

                        {/* Martingala */}
                        {candle.isMartingale && (
                          <>
                            <rect
                              x={x - 8}
                              y={50}
                              width={16}
                              height={12}
                              fill={candle.entryType === 'win' ? '#10b981' : '#ef4444'}
                              stroke="#ffffff"
                              strokeWidth="1"
                              rx="2"
                            />
                            <text
                              x={x}
                              y={58}
                              textAnchor="middle"
                              fontSize="8"
                              fill="#ffffff"
                              className="font-bold"
                            >
                              MG{candle.martingaleLevel}
                            </text>
                          </>
                        )}

                        <text
                          x={x}
                          y={candle.isPrimaryEntry ? 55 : 70}
                          textAnchor="middle"
                          fontSize="8"
                          fill="#9ca3af"
                        >
                          {candle.entryDirection}
                        </text>
                      </g>
                    )}
                  </g>
                )
              })}
            </svg>

            {/* Etiquetas de precio */}
            <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-300 -ml-20 py-2">
              <span className="bg-gray-800 px-2 py-1 rounded">{maxPrice.toFixed(4)}</span>
              <span className="bg-gray-800 px-2 py-1 rounded">{((maxPrice + minPrice) / 2).toFixed(4)}</span>
              <span className="bg-gray-800 px-2 py-1 rounded">{minPrice.toFixed(4)}</span>
            </div>

            {/* Timeline */}
            <div className="absolute bottom-0 left-0 w-full flex justify-between text-xs text-gray-400 mt-2 px-2">
              {data.filter((_, i) => i % Math.floor(data.length / 8) === 0).map((candle, index) => (
                <span key={index} className="bg-gray-800 px-2 py-1 rounded whitespace-nowrap">
                  {candle.date} {candle.time}
                </span>
              ))}
            </div>

            {/* Tooltip mejorado */}
            {hoveredCandle && (
              <div
                className="absolute z-50 bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg pointer-events-none"
                style={{
                  left: Math.min(hoveredCandle.x + 15, chartWidth - 200),
                  top: Math.max(hoveredCandle.y - 120, 10),
                  maxWidth: '190px'
                }}
              >
                <div className="text-xs space-y-1">
                  <div className="text-white font-semibold border-b border-gray-600 pb-1">
                    {hoveredCandle.candle.date} {hoveredCandle.candle.time}
                  </div>
                  <div className="grid grid-cols-2 gap-x-2 text-gray-300">
                    <div>Open:</div><div className="text-white text-right">{hoveredCandle.candle.open}</div>
                    <div>High:</div><div className="text-green-400 text-right">{hoveredCandle.candle.high}</div>
                    <div>Low:</div><div className="text-red-400 text-right">{hoveredCandle.candle.low}</div>
                    <div>Close:</div><div className="text-right">{hoveredCandle.candle.close}</div>
                  </div>

                  {hoveredCandle.candle.fragmentNumber && (
                    <div className="border-t border-gray-600 pt-1 mt-1">
                      <div className="text-xs text-purple-400">
                        Fragmento #{hoveredCandle.candle.fragmentNumber}
                      </div>
                    </div>
                  )}

                  {hoveredCandle.candle.isPatternCandle && (
                    <div className="border-t border-gray-600 pt-1 mt-1">
                      <div className="text-xs font-medium text-yellow-400">
                        Patrón: Vela {(hoveredCandle.candle.patternPosition || 0) + 1}/5
                      </div>
                    </div>
                  )}

                  {hoveredCandle.candle.isEntry && (
                    <div className="border-t border-gray-600 pt-1 mt-1">
                      <div className={`text-xs font-medium ${hoveredCandle.candle.entryType === 'win' ? 'text-green-400' : 'text-red-400'}`}>
                        {hoveredCandle.candle.isPrimaryEntry ? 'Entrada Principal' : `Martingala MG${hoveredCandle.candle.martingaleLevel}`}
                      </div>
                      <div className="text-xs text-gray-400">
                        {hoveredCandle.candle.entryDirection}: {hoveredCandle.candle.entryType === 'win' ? 'GANADA' : 'PERDIDA'}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Leyenda mejorada */}
        <div className="mt-4 p-3 bg-gray-800 rounded border text-xs">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-purple-500 border border-purple-400" style={{ borderStyle: 'dashed' }}></div>
              <span>Fragmentos (cada 5 velas)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 border-2 border-yellow-600"></div>
              <span>Velas del patrón</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-0 h-0 border-l-[6px] border-r-[6px] border-b-[8px] border-l-transparent border-r-transparent border-b-green-500"></div>
              <span>Entrada principal</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-2 bg-red-500 border border-white rounded"></div>
              <span>Martingala (MG1, MG2)</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Datos para el gráfico
  const priceData = candleData.map((candle, index) => ({
    index,
    price: candle.close,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
    date: candle.date,
    time: candle.time,
    isEntry: candle.isEntry,
    entryType: candle.entryType,
    isPatternStart: candle.isPatternStart,
    isPatternCandle: candle.isPatternCandle,
    patternType: candle.patternType,
    patternPosition: candle.patternPosition,
    entryDirection: candle.entryDirection,
    isFragmentStart: candle.isFragmentStart,
    fragmentNumber: candle.fragmentNumber,
    isPrimaryEntry: candle.isPrimaryEntry,
    isMartingale: candle.isMartingale,
    martingaleLevel: candle.martingaleLevel
  }))

  if (loading || !strategy) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white text-lg">Cargando detalle de estrategia...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      {/* Header */}
      <div className="border-b border-gray-700 bg-black/20 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.back()}
                className="flex items-center space-x-2 bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg transition-all"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Volver</span>
              </button>

              <div>
                <div className="flex items-center space-x-3">
                  <h1 className="text-3xl font-bold text-white">
                    {strategy.pair}
                  </h1>
                  <span className="bg-blue-600 px-3 py-1 rounded text-lg">
                    {strategy.timeframe}
                  </span>
                  {getDirectionIcon(strategy.direction)}
                </div>
                <p className="text-gray-300 mt-1">
                  Patrón: <span className="text-blue-400 font-mono">{strategy.pattern}</span> → {strategy.direction}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-6">
              <div className="text-center">
                <p className="text-sm text-gray-400">Efectividad</p>
                <p className={`text-2xl font-bold ${getEffectivenessColor(strategy.effectiveness)}`}>
                  {strategy.effectiveness.toFixed(1)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Score</p>
                <p className="text-xl font-bold text-blue-400">
                  {strategy.score.toFixed(1)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Estadísticas */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <Target className="w-8 h-8 text-green-400 mb-2" />
            <p className="text-2xl font-bold text-green-400">{strategy.wins}</p>
            <p className="text-gray-400">Operaciones Ganadoras</p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <Target className="w-8 h-8 text-red-400 mb-2" />
            <p className="text-2xl font-bold text-red-400">{strategy.losses}</p>
            <p className="text-gray-400">Operaciones Perdedoras</p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <BarChart3 className="w-8 h-8 text-yellow-400 mb-2" />
            <p className="text-2xl font-bold text-yellow-400">{strategy.occurrences}</p>
            <p className="text-gray-400">Total Ocurrencias</p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <Calendar className="w-8 h-8 text-blue-400 mb-2" />
            <p className="text-lg font-bold text-blue-400">
              {strategy.avg_profit.toFixed(3)}
            </p>
            <p className="text-gray-400">Ganancia Promedio</p>
          </div>
        </div>

        {/* Leyenda */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-gray-600 mb-8">
          <h3 className="text-lg font-bold mb-3">Análisis de Patrones OBPlus - Fragmentos de 5 Velas</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-purple-500 border-2 border-purple-600" style={{ borderStyle: 'dashed' }}></div>
              <span className="text-sm">Divisiones de fragmentos (cada 5 velas)</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-yellow-500 rounded-full border-2 border-yellow-600"></div>
              <span className="text-sm">Velas del patrón <span className="font-mono bg-gray-700 px-2 py-1 rounded">{strategy.pattern}</span></span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-green-500"></div>
              <span className="text-sm text-green-400">Entrada principal ganadora</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-red-500"></div>
              <span className="text-sm text-red-400">Entrada principal perdedora</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-4 h-3 bg-blue-500 border border-white rounded"></div>
              <span className="text-sm text-blue-400">Martingala MG1, MG2</span>
            </div>
          </div>
          <div className="mt-3 text-sm text-gray-400">
            <strong>Metodología OBPlus:</strong> Detectar patrón &ldquo;{strategy.pattern}&rdquo; en fragmentos de 5 velas → Entrada {strategy.direction} según la estrategia específica
          </div>
        </div>

        {/* Filtros */}
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-6 gap-4">
          <h2 className="text-2xl font-bold">Análisis Histórico con Fragmentos OBPlus</h2>

          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm text-gray-400 font-medium">Rango de Tiempo:</label>
              <div className="flex space-x-2">
                {['1W', '1M', '3M', '6M', '1Y'].map((range) => (
                  <button
                    key={range}
                    onClick={() => setSelectedTimeRange(range)}
                    className={`px-3 py-2 rounded-lg transition-all text-sm ${
                      selectedTimeRange === range
                        ? 'bg-purple-600 text-white'
                        : 'bg-white/10 text-gray-300 hover:bg-white/20'
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm text-gray-400 font-medium">Período de Vela:</label>
              <div className="flex space-x-2">
                {['1h', '1d', '1w', '1M'].map((size) => (
                  <button
                    key={size}
                    onClick={() => setSelectedCandleSize(size)}
                    className={`px-3 py-2 rounded-lg transition-all text-sm ${
                      selectedCandleSize === size
                        ? 'bg-blue-600 text-white'
                        : 'bg-white/10 text-gray-300 hover:bg-white/20'
                    }`}
                  >
                    {size}
                  </button>
                ))}
                <div className="flex items-center px-2 text-xs text-green-400">
                  Datos reales
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Gráfico de velas mejorado */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold">Gráfico OBPlus - Análisis de Fragmentos - {strategy.pair}</h3>
              <p className="text-sm text-gray-400 mt-1">
                Velas de {selectedCandleSize} • Rango: {selectedTimeRange} • {candleData.length} velas • Fragmentos de 5 velas no solapados
              </p>
            </div>
          </div>

          <div className="h-96 mb-6">
            <ImprovedCandlestickChart data={priceData} />
          </div>
        </div>

        {/* Estadísticas de patrones OBPlus */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <h3 className="text-lg font-bold mb-4">Análisis de Fragmentos OBPlus</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span>Fragmentos analizados:</span>
                <span className="font-bold text-purple-400">
                  {candleData.filter(c => c.isFragmentStart).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Patrones detectados:</span>
                <span className="font-bold text-yellow-400">
                  {candleData.filter(c => c.isPatternCandle && c.patternPosition === 0).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Entradas principales:</span>
                <span className="font-bold">{candleData.filter(c => c.isPrimaryEntry).length}</span>
              </div>
              <div className="flex justify-between">
                <span>Entradas con martingala:</span>
                <span className="font-bold">{candleData.filter(c => c.isMartingale).length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-green-400">Entradas ganadoras:</span>
                <span className="font-bold text-green-400">
                  {candleData.filter(c => c.isEntry && c.entryType === 'win').length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-400">Entradas perdedoras:</span>
                <span className="font-bold text-red-400">
                  {candleData.filter(c => c.isEntry && c.entryType === 'loss').length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-400">Tasa de éxito real:</span>
                <span className="font-bold text-blue-400">
                  {candleData.filter(c => c.isEntry).length > 0
                    ? ((candleData.filter(c => c.isEntry && c.entryType === 'win').length / candleData.filter(c => c.isEntry).length) * 100).toFixed(1)
                    : 0}%
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <h3 className="text-lg font-bold mb-4">Últimas Operaciones</h3>
            <div className="space-y-3 max-h-60 overflow-y-auto">
              {candleData
                .filter(candle => candle.isEntry)
                .slice(-10)
                .reverse()
                .map((candle, index) => (
                  <div
                    key={index}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      candle.entryType === 'win'
                        ? 'bg-green-500/10 border-green-500/30'
                        : 'bg-red-500/10 border-red-500/30'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${
                        candle.entryType === 'win' ? 'bg-green-500' : 'bg-red-500'
                      }`}></div>
                      <div>
                        <div className="font-medium">{candle.date} {candle.time}</div>
                        <div className="text-sm text-gray-400">
                          Precio: {candle.close.toFixed(5)} • {candle.entryDirection}
                          {candle.isMartingale && ` • MG${candle.martingaleLevel}`}
                        </div>
                      </div>
                    </div>
                    <div className={`font-bold ${
                      candle.entryType === 'win' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {candle.entryType === 'win' ? '✓' : '✗'}
                    </div>
                  </div>
                ))
              }
              {candleData.filter(candle => candle.isEntry).length === 0 && (
                <div className="text-center text-gray-400 py-4">
                  No se encontraron entradas para el patrón &ldquo;{strategy.pattern}&rdquo;
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Gráfico de línea */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold">Línea de Precios con Marcadores OBPlus</h3>
            <div className="text-sm text-gray-400">
              Rango: {selectedTimeRange} • Mostrando {priceData.length} velas
            </div>
          </div>

          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="index"
                  stroke="#9CA3AF"
                  tickFormatter={(value) => {
                    const candle = candleData[value]
                    return candle ? `${candle.date} ${candle.time}` : ''
                  }}
                />
                <YAxis
                  stroke="#9CA3AF"
                  domain={['dataMin - 0.001', 'dataMax + 0.001']}
                  tickFormatter={(value) => value.toFixed(4)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: '1px solid #4B5563',
                    borderRadius: '8px'
                  }}
                  labelFormatter={(value) => {
                    const candle = candleData[value as number]
                    return candle ? `${candle.date} ${candle.time}` : ''
                  }}
                  formatter={(value: number) => [value.toFixed(5), 'Precio']}
                />
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  dot={false}
                />

                {priceData.filter(d => d.isEntry && d.entryType === 'win').map((entry, index) => (
                  <ReferenceDot
                    key={`win-${index}`}
                    x={entry.index}
                    y={entry.price}
                    r={6}
                    fill="#10B981"
                    stroke="#ffffff"
                    strokeWidth={2}
                  />
                ))}

                {priceData.filter(d => d.isEntry && d.entryType === 'loss').map((entry, index) => (
                  <ReferenceDot
                    key={`loss-${index}`}
                    x={entry.index}
                    y={entry.price}
                    r={6}
                    fill="#EF4444"
                    stroke="#ffffff"
                    strokeWidth={2}
                  />
                ))}

                {priceData.filter(d => d.isFragmentStart).map((pattern, index) => (
                  <ReferenceDot
                    key={`fragment-${index}`}
                    x={pattern.index}
                    y={pattern.price}
                    r={3}
                    fill="#8B5CF6"
                    stroke="#ffffff"
                    strokeWidth={1}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tabla detallada */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg border border-gray-600 overflow-hidden">
          <div className="p-6 border-b border-gray-600">
            <h3 className="text-xl font-bold">Historial Detallado de Análisis OBPlus</h3>
            <p className="text-gray-400 mt-1">
              Últimas 20 velas con análisis de fragmentos, patrones y entradas
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-black/20">
                <tr>
                  <th className="px-4 py-3 text-left">Fecha/Hora</th>
                  <th className="px-4 py-3 text-right">Open</th>
                  <th className="px-4 py-3 text-right">High</th>
                  <th className="px-4 py-3 text-right">Low</th>
                  <th className="px-4 py-3 text-right">Close</th>
                  <th className="px-4 py-3 text-center">Color</th>
                  <th className="px-4 py-3 text-center">Fragmento</th>
                  <th className="px-4 py-3 text-center">Patrón</th>
                  <th className="px-4 py-3 text-center">Entrada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {candleData.slice(-20).reverse().map((candle, index) => (
                  <tr
                    key={index}
                    className={`hover:bg-white/5 ${
                      candle.isEntry ? (candle.entryType === 'win' ? 'bg-green-500/5' : 'bg-red-500/5') : ''
                    } ${
                      candle.isPatternCandle ? 'bg-yellow-500/5' : ''
                    } ${
                      candle.isFragmentStart ? 'bg-purple-500/5' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium">{candle.date}</p>
                        <p className="text-sm text-gray-400">{candle.time}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">{candle.open}</td>
                    <td className="px-4 py-3 text-right font-mono">{candle.high}</td>
                    <td className="px-4 py-3 text-right font-mono">{candle.low}</td>
                    <td className="px-4 py-3 text-right font-mono">{candle.close}</td>
                    <td className="px-4 py-3 text-center">
                      <div className={`w-4 h-4 rounded mx-auto ${
                        candle.color === 'green' ? 'bg-green-500' : 'bg-red-500'
                      }`}></div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {candle.isFragmentStart && (
                        <span className="bg-purple-500 text-white px-2 py-1 rounded text-xs font-medium">
                          #{candle.fragmentNumber}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {candle.isPatternCandle && (
                        <span className="bg-yellow-500 text-black px-2 py-1 rounded text-xs font-medium">
                          Pos {(candle.patternPosition || 0) + 1}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {candle.isEntry && (
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          candle.entryType === 'win'
                            ? 'bg-green-600 text-white'
                            : 'bg-red-600 text-white'
                        }`}>
                          {candle.isPrimaryEntry ? 'PRINCIPAL' : `MG${candle.martingaleLevel}`}
                          {' '}
                          {candle.entryDirection} {candle.entryType === 'win' ? 'WIN' : 'LOSS'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}