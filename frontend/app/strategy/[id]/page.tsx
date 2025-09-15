'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { createClient } from '@supabase/supabase-js'
import { ArrowLeft, TrendingUp, TrendingDown, Calendar, Target, BarChart3 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot, ComposedChart, Bar } from 'recharts'

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
}

export default function StrategyDetail() {
  const params = useParams()
  const router = useRouter()
  const strategyId = params.id as string

  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [candleData, setCandleData] = useState<CandleData[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTimeRange, setSelectedTimeRange] = useState('1M') // 1 mes por defecto

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

  useEffect(() => {
    if (strategyId) {
      fetchStrategyDetail()
      generateMockCandleData()
    }
  }, [strategyId, fetchStrategyDetail])

  useEffect(() => {
    // Regenerar datos cuando cambia el rango de tiempo
    generateMockCandleData()
  }, [selectedTimeRange])

  // Generar datos simulados de velas para demostración
  const generateMockCandleData = useCallback(() => {
    const data: CandleData[] = []
    const basePrice = 1.0850 // EUR/USD ejemplo
    let currentPrice = basePrice
    
    // Determinar cantidad de velas según el rango seleccionado
    const candleCount = {
      '1W': 672,    // 7 días * 4 velas por hora (15m)
      '1M': 2880,   // 30 días * 4 velas por hora
      '3M': 8640,   // 90 días * 4 velas por hora
      '6M': 17280,  // 180 días * 4 velas por hora
      '1Y': 35040   // 365 días * 4 velas por hora
    }
    
    const totalCandles = candleCount[selectedTimeRange as keyof typeof candleCount] || 2880
    const hoursBetween = selectedTimeRange === '1W' ? 0.25 : selectedTimeRange === '1M' ? 0.25 : 0.25 // 15 minutos
    
    // Generar velas con patrones más realistas
    for (let i = 0; i < totalCandles; i++) {
      const date = new Date(Date.now() - (totalCandles - i) * hoursBetween * 60 * 60 * 1000)
      
      // Crear movimientos más naturales con ciclos
      const dailyCycle = Math.sin((i / (24 * 4)) * 2 * Math.PI) * 0.003 // Ciclo diario
      const weeklyCycle = Math.sin((i / (24 * 7 * 4)) * 2 * Math.PI) * 0.008 // Ciclo semanal
      const randomNoise = (Math.random() - 0.5) * 0.004 // Ruido aleatorio
      const trend = Math.sin(i / 1000) * 0.02 // Tendencia a largo plazo
      
      const movement = dailyCycle + weeklyCycle + randomNoise + trend
      
      const open = currentPrice
      const volatility = 0.002 + Math.abs(Math.sin(i / 200)) * 0.003 // Volatilidad variable
      
      // Crear precio de cierre más natural
      const close = open + movement + (Math.random() - 0.5) * volatility
      
      // High y Low más realistas
      const bodyRange = Math.abs(close - open)
      const wickMultiplier = 0.5 + Math.random() * 1.5
      
      const high = Math.max(open, close) + (bodyRange * wickMultiplier + Math.random() * volatility * 0.5)
      const low = Math.min(open, close) - (bodyRange * wickMultiplier + Math.random() * volatility * 0.5)
      
      const isGreen = close > open
      
      // Simular entradas de trading más espaciadas y realistas
      const shouldHaveEntry = Math.random() < 0.02 && i > 50 // Solo 2% probabilidad
      const entrySuccess = Math.random() < (strategy?.effectiveness || 95) / 100 // Usar efectividad real
      
      data.push({
        date: date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' }),
        time: date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
        open: parseFloat(open.toFixed(5)),
        high: parseFloat(high.toFixed(5)),
        low: parseFloat(low.toFixed(5)),
        close: parseFloat(close.toFixed(5)),
        color: isGreen ? 'green' : 'red',
        isPatternStart: i > 10 && Math.random() < 0.03, // 3% chance patrón detectado
        isEntry: shouldHaveEntry,
        entryType: shouldHaveEntry ? (entrySuccess ? 'win' : 'loss') : undefined
      })
      
      currentPrice = close
    }
    
    setCandleData(data)
  }, [selectedTimeRange, strategy?.effectiveness])

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

  // Componente personalizado para renderizar velas japonesas
  const CandlestickChart = ({ data }: { data: typeof priceData }) => {
    // Determinar cuántas velas mostrar según el rango
    const candlesToShow = {
      '1W': 200,   // 200 velas para 1 semana
      '1M': 400,   // 400 velas para 1 mes
      '3M': 600,   // 600 velas para 3 meses
      '6M': 800,   // 800 velas para 6 meses
      '1Y': 1000   // 1000 velas para 1 año
    }
    
    const maxCandles = candlesToShow[selectedTimeRange as keyof typeof candlesToShow] || 400
    const displayData = data.slice(-maxCandles) // Mostrar las más recientes
    
    if (displayData.length === 0) return <div>No hay datos disponibles</div>
    
    const maxPrice = Math.max(...displayData.map(d => d.high || d.price))
    const minPrice = Math.min(...displayData.map(d => d.low || d.price))
    const priceRange = maxPrice - minPrice || 0.001
    const chartHeight = 400
    const chartWidth = Math.max(displayData.length * 8, 1000) // Mínimo 8px por vela
    
    return (
      <div className="relative w-full overflow-x-auto bg-gray-900 rounded-lg">
        <div className="relative" style={{ width: chartWidth + 'px', height: chartHeight + 'px' }}>
          <svg width={chartWidth} height={chartHeight} className="overflow-visible">
            {/* Grid lines horizontales */}
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
            
            {/* Grid lines verticales */}
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
              const x = index * 8 + 4 // 8px de espacio por vela
              const candleWidth = 6 // Ancho fijo en pixels
              
              const open = candle.open || candle.price
              const high = candle.high || candle.price
              const low = candle.low || candle.price
              const close = candle.close || candle.price
              
              // Normalizar precios a coordenadas Y
              const openY = chartHeight - ((open - minPrice) / priceRange) * chartHeight
              const highY = chartHeight - ((high - minPrice) / priceRange) * chartHeight
              const lowY = chartHeight - ((low - minPrice) / priceRange) * chartHeight
              const closeY = chartHeight - ((close - minPrice) / priceRange) * chartHeight
              
              const isGreen = close > open
              const bodyTop = Math.min(openY, closeY)
              const bodyHeight = Math.max(Math.abs(closeY - openY), 1) // Mínimo 1px de altura
              
              return (
                <g key={index}>
                  {/* Línea superior e inferior (mechas) */}
                  <line
                    x1={x}
                    x2={x}
                    y1={highY}
                    y2={lowY}
                    stroke={isGreen ? '#10B981' : '#EF4444'}
                    strokeWidth="1"
                  />
                  
                  {/* Cuerpo de la vela */}
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
                  
                  {/* Puntos de entrada */}
                  {candle.isEntry && (
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
                  
                  {/* Patrones detectados */}
                  {candle.isPatternStart && (
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
          
          {/* Etiquetas de precio en el eje Y */}
          <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-300 -ml-20 py-2">
            <span className="bg-gray-800 px-2 py-1 rounded">{maxPrice.toFixed(4)}</span>
            <span className="bg-gray-800 px-2 py-1 rounded">{((maxPrice + minPrice) / 2).toFixed(4)}</span>
            <span className="bg-gray-800 px-2 py-1 rounded">{minPrice.toFixed(4)}</span>
          </div>
          
          {/* Timeline en la parte inferior */}
          <div className="absolute bottom-0 left-0 w-full flex justify-between text-xs text-gray-400 -mb-6">
            {displayData.filter((_, i) => i % Math.floor(displayData.length / 6) === 0).map((candle, index) => (
              <span key={index} className="bg-gray-800 px-2 py-1 rounded">
                {candle.date} {candle.time}
              </span>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Datos para el gráfico de línea de precios (datos originales extendidos)
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
    isPatternStart: candle.isPatternStart
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
        {/* Estadísticas de la estrategia */}
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

        {/* Filtros de tiempo */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Análisis Histórico de Velas</h2>
          <div className="flex space-x-2">
            {['1W', '1M', '3M', '6M', '1Y'].map((range) => (
              <button
                key={range}
                onClick={() => setSelectedTimeRange(range)}
                className={`px-4 py-2 rounded-lg transition-all ${
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

        {/* Gráfico de velas japonesas */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold">Gráfico de Velas Japonesas - {strategy.pair}</h3>
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
          
          {/* Timeline inferior */}
          <div className="flex justify-between text-xs text-gray-400 mt-2">
            {priceData.slice(-50).filter((_, i) => i % 10 === 0).map((candle, index) => (
              <span key={index}>{candle.date} {candle.time}</span>
            ))}
          </div>
        </div>

        {/* Gráfico de línea adicional para contexto */}
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
                
                {/* Puntos de entrada ganadores */}
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
                
                {/* Puntos de entrada perdedores */}
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
                
                {/* Puntos de patrones detectados */}
                {priceData.filter(d => d.isPatternStart).map((pattern, index) => (
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

        {/* Tabla de velas detallada */}
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
                  <tr key={index} className="hover:bg-white/5">
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
                      {candle.isPatternStart && (
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
                          {candle.entryType === 'win' ? 'WIN' : 'LOSS'}
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