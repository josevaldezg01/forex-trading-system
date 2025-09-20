'use client'

import { useState, useEffect, useCallback } from 'react'
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
    
    const candlesWithPatterns = strategy ? detectPatterns(data, strategy) : data
    setCandleData(candlesWithPatterns)
    console.log('Usando datos simulados como fallback')
  }, [strategy])

  // Función para detectar patrones automáticamente
  const detectPatterns = useCallback((candles: CandleData[], strategy: Strategy) => {
    if (!strategy || !candles.length) return candles

    const candlesWithPatterns = [...candles]
    const pattern = strategy.pattern || 'RRR'
    const direction = strategy.direction || 'CALL'
    
    // Convertir velas a secuencia R/V
    const sequence = candles.map(candle => 
      candle.close >= candle.open ? 'V' : 'R'
    )
    
    // Buscar coincidencias del patrón
    for (let i = 0; i <= sequence.length - pattern.length - 1; i++) {
      const currentSequence = sequence.slice(i, i + pattern.length).join('')
      
      if (currentSequence === pattern) {
        // Marcar las velas del patrón
        for (let j = 0; j < pattern.length; j++) {
          candlesWithPatterns[i + j] = {
            ...candlesWithPatterns[i + j],
            isPatternCandle: true,
            patternPosition: j,
            patternType: pattern[j],
            isPatternStart: j === 0
          }
        }
        
        // Marcar la vela de entrada (siguiente al patrón)
        const entryIndex = i + pattern.length
        if (entryIndex < candlesWithPatterns.length) {
          const entryCandle = candlesWithPatterns[entryIndex]
          const isEntryCorrect = direction === 'CALL' 
            ? entryCandle.close >= entryCandle.open 
            : entryCandle.close < entryCandle.open
          
          candlesWithPatterns[entryIndex] = {
            ...entryCandle,
            isEntry: true,
            entryType: isEntryCorrect ? 'win' : 'loss',
            entryDirection: direction
          }
        }
      }
    }
    
    return candlesWithPatterns
  }, [])

  // Cargar datos reales de Supabase
  const fetchRealCandleData = useCallback(async () => {
    if (!strategy) return
    
    try {
      setLoading(true)
      
      const pair = strategy.pair.replace('/', '')
      const availableTimeframes = ['1h', '1d']
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
      
      const candlesWithPatterns = detectPatterns(realCandles, strategy)
      setCandleData(candlesWithPatterns)
      console.log(`Cargados ${candlesWithPatterns.length} datos reales para ${pair} ${actualTimeframe}`)
      
    } catch (error) {
      console.error('Error fetching real data:', error)
      generateFallbackData()
    } finally {
      setLoading(false)
    }
  }, [strategy, selectedTimeRange, selectedCandleSize, detectPatterns, generateFallbackData])

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

  // Componente de gráfico de velas
  const CandlestickChart = ({ data }: { data: typeof priceData }) => {
    const candlesToShow = {
      '1W': 200,
      '1M': 400,
      '3M': 600,
      '6M': 800,
      '1Y': 1000
    }
    
    const maxCandles = candlesToShow[selectedTimeRange as keyof typeof candlesToShow] || 400
    const displayData = data.slice(-maxCandles)
    
    if (displayData.length === 0) return <div>No hay datos disponibles</div>
    
    const maxPrice = Math.max(...displayData.map(d => d.high || d.price))
    const minPrice = Math.min(...displayData.map(d => d.low || d.price))
    const priceRange = maxPrice - minPrice || 0.001
    const chartHeight = 400
    const chartWidth = Math.max(displayData.length * 8, 1000)
    
const handleMouseMove = (event: React.MouseEvent<SVGSVGElement>) => {
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top  // Agrega esta línea que faltaba

  const candleIndex = Math.floor(x / 8)

  if (candleIndex >= 0 && candleIndex < displayData.length) {
    const candle = displayData[candleIndex]
    const foundCandle = candleData.find(c =>
      c.date === candle.date && c.time === candle.time
    )

    if (foundCandle) {
      setHoveredCandle({
        candle: foundCandle,
        x: x,  // Usar coordenada relativa, no event.clientX
        y: y   // Usar coordenada relativa, no event.clientY
      })
    }
  }
}
    
    const handleMouseLeave = () => {
      setHoveredCandle(null)
    }
return (
  <div className="relative w-full bg-gray-900 rounded-lg">
    <div
      className="overflow-x-auto overflow-y-hidden"
      style={{ height: chartHeight + 60 + 'px' }} // Espacio extra para timeline
    >
      <div className="relative" style={{ width: chartWidth + 'px', height: chartHeight + 'px' }}>
        <svg
          width={chartWidth}
          height={chartHeight}
          className="overflow-visible cursor-crosshair"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
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
            
            {Array.from({ length: Math.floor(displayData.length / 20) }, (_, i) => i * 20).map((index) => (
              <line
                key={index}
                x1={index * 8}
                x2={index * 8}
                y1="0"
                y2={chartHeight}
                stroke="#374151"
                strokeDasharray="2 2"
                strokeWidth="0.5"
              />
            ))}
            
            {/* Render candles */}
            {displayData.map((candle, index) => {
              const x = index * 8 + 4
              const candleWidth = 6
              
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
                  <rect
                    x={x - 4}
                    y={0}
                    width={8}
                    height={chartHeight}
                    fill="transparent"
                    className="hover:fill-white hover:fill-opacity-5"
                  />
                  
                  <line
                    x1={x}
                    x2={x}
                    y1={highY}
                    y2={lowY}
                    stroke={isGreen ? '#10B981' : '#EF4444'}
                    strokeWidth="1"
                  />
                  
                  <rect
                    x={x - candleWidth/2}
                    y={bodyTop}
                    width={candleWidth}
                    height={bodyHeight}
                    fill={isGreen ? '#10B981' : '#EF4444'}
                    stroke={isGreen ? '#10B981' : '#EF4444'}
                    strokeWidth="1"
                    opacity="0.9"
                  />
                  
                  {/* Marcadores del patrón debajo */}
                  {candle.isPatternCandle && (
                    <g>
                      <circle
                        cx={x}
                        cy={chartHeight - 25}
                        r="6"
                        fill="#fbbf24"
                        stroke="#f59e0b"
                        strokeWidth="2"
                      />
                      <text
                        x={x}
                        y={chartHeight - 21}
                        textAnchor="middle"
                        fontSize="10"
                        fill="#000"
                        className="font-bold"
                      >
                        {candle.patternType}
                      </text>
                    </g>
                  )}
                  
                  {/* Marcador de entrada arriba */}
                  {candle.isEntry && (
                    <g>
                      <polygon
                        points={`${x-8},30 ${x+8},30 ${x},15`}
                        fill={candle.entryType === 'win' ? '#10b981' : '#ef4444'}
                        stroke={candle.entryType === 'win' ? '#059669' : '#dc2626'}
                        strokeWidth="2"
                      />
                      
                      <text
                        x={x}
                        y={10}
                        textAnchor="middle"
                        fontSize="9"
                        fill={candle.entryType === 'win' ? '#10b981' : '#ef4444'}
                        className="font-bold"
                      >
                        {candle.entryType === 'win' ? 'GANADA' : 'PERDIDA'}
                      </text>
                      
                      <text
                        x={x}
                        y={45}
                        textAnchor="middle"
                        fontSize="8"
                        fill="#9ca3af"
                      >
                        {candle.entryDirection}
                      </text>
                    </g>
                  )}
                  
                  {/* Compatibilidad con marcadores originales */}
                  {candle.isEntry && !candle.entryDirection && (
                    <circle
                      cx={x}
                      cy={closeY - 15}
                      r="5"
                      fill={candle.entryType === 'win' ? '#10B981' : '#EF4444'}
                      stroke="#ffffff"
                      strokeWidth="2"
                      opacity="0.9"
                    />
                  )}
                  
                  {candle.isPatternStart && !candle.isPatternCandle && (
                    <polygon
                      points={`${x},${closeY - 25} ${x-4},${closeY - 15} ${x+4},${closeY - 15}`}
                      fill="#F59E0B"
                      stroke="#ffffff"
                      strokeWidth="1"
                    />
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
          
        {/* Timeline DENTRO del contenedor scrolleable */}
        <div className="absolute bottom-0 left-0 w-full flex justify-between text-xs text-gray-400 mt-2 px-2">
          {displayData.filter((_, i) => i % Math.floor(displayData.length / 6) === 0).map((candle, index) => (
            <span key={index} className="bg-gray-800 px-2 py-1 rounded whitespace-nowrap">
              {candle.date} {candle.time}
            </span>
          ))}
        </div>

        {/* Tooltip DENTRO del contenedor */}
        {hoveredCandle && (
          <div
            className="absolute z-50 bg-gray-800 border border-gray-600 rounded-lg p-2 shadow-lg pointer-events-none"
            style={{
              left: Math.min(hoveredCandle.x + 15, chartWidth - 180),
              top: Math.max(hoveredCandle.y - 90, 10),
              maxWidth: '170px'
            }}
          >
    <div className="text-xs space-y-1">
      <div className="text-white font-semibold border-b border-gray-600 pb-1">
        {hoveredCandle.candle.date} {hoveredCandle.candle.time}
      </div>
      <div className="grid grid-cols-2 gap-x-2 text-gray-300"> {/* Reducir gap */}
        <div>Open:</div>
        <div className="text-white text-right">{hoveredCandle.candle.open}</div>
        <div>High:</div>
        <div className="text-green-400 text-right">{hoveredCandle.candle.high}</div>
        <div>Low:</div>
        <div className="text-red-400 text-right">{hoveredCandle.candle.low}</div>
        <div>Close:</div>
        <div className={`text-right ${hoveredCandle.candle.close > hoveredCandle.candle.open ? 'text-green-400' : 'text-red-400'}`}>
          {hoveredCandle.candle.close}
        </div>
      </div>

      {hoveredCandle.candle.isPatternCandle && (
        <div className="border-t border-gray-600 pt-1 mt-1">
          <div className="text-xs font-medium text-yellow-400">
            Patrón: {hoveredCandle.candle.patternType} (Pos. {(hoveredCandle.candle.patternPosition || 0) + 1})
          </div>
        </div>
      )}

      {hoveredCandle.candle.isEntry && (
        <div className="border-t border-gray-600 pt-1 mt-1">
          <div className={`text-xs font-medium ${hoveredCandle.candle.entryType === 'win' ? 'text-green-400' : 'text-red-400'}`}>
            Entrada {hoveredCandle.candle.entryDirection || 'DESCONOCIDA'}: {hoveredCandle.candle.entryType === 'win' ? 'GANADORA' : 'PERDEDORA'}
          </div>
        </div>
      )}

      {hoveredCandle.candle.isEntry && !hoveredCandle.candle.entryDirection && (
        <div className="border-t border-gray-600 pt-1 mt-1">
          <div className={`text-xs font-medium ${hoveredCandle.candle.entryType === 'win' ? 'text-green-400' : 'text-red-400'}`}>
            Entrada: {hoveredCandle.candle.entryType === 'win' ? 'GANADORA' : 'PERDEDORA'}
          </div>
        </div>
      )}

      {hoveredCandle.candle.isPatternStart && !hoveredCandle.candle.isPatternCandle && (
        <div className="border-t border-gray-600 pt-1 mt-1">
          <div className="text-xs font-medium text-yellow-400">
            Patrón detectado: {strategy?.pattern}
          </div>
        </div>
      )}
    </div>
  </div>
)}
      </div>
    </div>
  </div>
)

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
  entryDirection: candle.entryDirection
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
          <h3 className="text-lg font-bold mb-3">Leyenda del Análisis de Patrones</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 bg-yellow-500 rounded-full border-2 border-yellow-600"></div>
              <span className="text-sm">Velas del patrón <span className="font-mono bg-gray-700 px-2 py-1 rounded">{strategy.pattern}</span></span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-green-500"></div>
              <span className="text-sm text-green-400">Entrada ganadora</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-0 h-0 border-l-[8px] border-r-[8px] border-b-[12px] border-l-transparent border-r-transparent border-b-red-500"></div>
              <span className="text-sm text-red-400">Entrada perdedora</span>
            </div>
          </div>
          <div className="mt-3 text-sm text-gray-400">
            <strong>Estrategia:</strong> Detectar patrón &ldquo;{strategy.pattern}&rdquo; → Entrada {strategy.direction} en la siguiente vela
          </div>
        </div>

        {/* Filtros */}
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-6 gap-4">
          <h2 className="text-2xl font-bold">Análisis Histórico de Velas</h2>
          
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
                {['1h', '1d'].map((size) => (
                  <button
                    key={size}
                    onClick={() => setSelectedCandleSize(size)}
                    className={`px-3 py-2 rounded-lg transition-all text-sm ${
                      selectedCandleSize === size
                        ? 'bg-blue-600 text-white'
                        : 'bg-white/10 text-gray-300 hover:bg-white/20'
                    }`}
                    title={`Velas de ${size} (datos reales de Yahoo Finance)`}
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

        {/* Gráfico de velas */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold">Gráfico de Velas Japonesas - {strategy.pair}</h3>
              <p className="text-sm text-gray-400 mt-1">
                Velas de {selectedCandleSize} • Rango: {selectedTimeRange} • {candleData.length} velas generadas
              </p>
            </div>
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>Operación Ganadora</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span>Operación Perdedora</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <span>Patrón Detectado</span>
              </div>
            </div>
          </div>
          
          <div className="h-96 mb-6">
            <CandlestickChart data={priceData} />
          </div>
          
          <div className="flex justify-between text-xs text-gray-400 mt-2">
            {priceData.slice(-50).filter((_, i) => i % 10 === 0).map((candle, index) => (
              <span key={index}>{candle.date} {candle.time}</span>
            ))}
          </div>
        </div>

        {/* Estadísticas de patrones */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <h3 className="text-lg font-bold mb-4">Análisis de Patrones</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span>Patrones detectados:</span>
                <span className="font-bold text-yellow-400">
                  {candleData.filter(c => c.isPatternCandle && c.patternPosition === 0).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Entradas ejecutadas:</span>
                <span className="font-bold">{candleData.filter(c => c.isEntry).length}</span>
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
                <span className="text-blue-400">Tasa de éxito:</span>
                <span className="font-bold text-blue-400">
                  {candleData.filter(c => c.isEntry).length > 0 
                    ? ((candleData.filter(c => c.isEntry && c.entryType === 'win').length / candleData.filter(c => c.isEntry).length) * 100).toFixed(1) 
                    : 0}%
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600">
            <h3 className="text-lg font-bold mb-4">Últimas Entradas</h3>
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
            <h3 className="text-xl font-bold">Línea de Precios y Contexto Histórico</h3>
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
                
                {priceData.filter(d => d.isPatternStart || d.isPatternCandle).map((pattern, index) => (
                  <ReferenceDot 
                    key={`pattern-${index}`}
                    x={pattern.index} 
                    y={pattern.price} 
                    r={4} 
                    fill="#F59E0B" 
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
            <h3 className="text-xl font-bold">Historial Detallado de Velas</h3>
            <p className="text-gray-400 mt-1">
              Últimas 20 velas con indicadores de patrones y entradas
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
                      {candle.isPatternCandle && (
                        <span className="bg-yellow-500 text-black px-2 py-1 rounded text-xs font-medium">
                          {candle.patternType} ({(candle.patternPosition || 0) + 1})
                        </span>
                      )}
                      {candle.isPatternStart && !candle.isPatternCandle && (
                        <span className="bg-yellow-500 text-black px-2 py-1 rounded text-xs font-medium">
                          {strategy.pattern}
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
   </div>
  </div>
  )
}