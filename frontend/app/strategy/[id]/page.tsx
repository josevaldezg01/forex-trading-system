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
      '1W': 168,   // 7 días * 24 horas
      '1M': 720,   // 30 días * 24 horas  
      '3M': 2160,  // 90 días * 24 horas
      '6M': 4320,  // 180 días * 24 horas
      '1Y': 8760   // 365 días * 24 horas
    }
    
    const totalCandles = candleCount[selectedTimeRange as keyof typeof candleCount] || 720
    
    // Generar velas
    for (let i = 0; i < totalCandles; i++) {
      const date = new Date(Date.now() - (totalCandles - i) * 60 * 60 * 1000) // Cada hora hacia atrás
      
      // Simulación de precio OHLC más realista
      const open = currentPrice
      const volatility = 0.0015 // Aumentar volatilidad para más realismo
      const trend = Math.sin(i / 100) * 0.0005 // Tendencia suave
      const change = (Math.random() - 0.5) * volatility + trend
      
      const high = open + Math.abs(change) + Math.random() * volatility * 0.3
      const low = open - Math.abs(change) - Math.random() * volatility * 0.3
      const close = open + change
      
      const isGreen = close > open
      
      // Simular entradas de trading cada 15-25 velas (más esparcidas)
      const shouldHaveEntry = Math.random() < 0.05 && i > 10
      const entrySuccess = Math.random() < 0.95 // 95% éxito como en los datos
      
      data.push({
        date: date.toLocaleDateString('es-ES'),
        time: date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
        open: parseFloat(open.toFixed(5)),
        high: parseFloat(high.toFixed(5)),
        low: parseFloat(low.toFixed(5)),
        close: parseFloat(close.toFixed(5)),
        color: isGreen ? 'green' : 'red',
        isPatternStart: i > 0 && Math.random() < 0.08, // 8% chance patrón detectado
        isEntry: shouldHaveEntry,
        entryType: shouldHaveEntry ? (entrySuccess ? 'win' : 'loss') : undefined
      })
      
      currentPrice = close
    }
    
    setCandleData(data)
  }, [selectedTimeRange])

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
    const maxPrice = Math.max(...data.map(d => Math.max(d.high || d.price, d.price)))
    const minPrice = Math.min(...data.map(d => Math.min(d.low || d.price, d.price)))
    const priceRange = maxPrice - minPrice
    const chartHeight = 300
    
    return (
      <div className="relative w-full" style={{ height: chartHeight + 'px' }}>
        <svg width="100%" height={chartHeight} className="overflow-visible">
          {/* Grid lines */}
          {[0.25, 0.5, 0.75].map((ratio, i) => (
            <line
              key={i}
              x1="0"
              x2="100%"
              y1={chartHeight * ratio}
              y2={chartHeight * ratio}
              stroke="#374151"
              strokeDasharray="3 3"
              strokeWidth="1"
            />
          ))}
          
          {/* Render candles */}
          {data.slice(-50).map((candle, index) => { // Mostrar últimas 50 velas
            const x = (index / 49) * 100 // Porcentaje de ancho
            const candleWidth = 1.8 // Ancho de vela en %
            
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
            const bodyHeight = Math.abs(closeY - openY)
            
            return (
              <g key={index}>
                {/* Línea superior e inferior */}
                <line
                  x1={`${x}%`}
                  x2={`${x}%`}
                  y1={highY}
                  y2={lowY}
                  stroke={isGreen ? '#10B981' : '#EF4444'}
                  strokeWidth="1"
                />
                
                {/* Cuerpo de la vela */}
                <rect
                  x={`${x - candleWidth/2}%`}
                  y={bodyTop}
                  width={`${candleWidth}%`}
                  height={bodyHeight || 1}
                  fill={isGreen ? '#10B981' : '#EF4444'}
                  stroke={isGreen ? '#10B981' : '#EF4444'}
                  strokeWidth="1"
                />
                
                {/* Puntos de entrada */}
                {candle.isEntry && (
                  <circle
                    cx={`${x}%`}
                    cy={closeY - 10}
                    r="4"
                    fill={candle.entryType === 'win' ? '#10B981' : '#EF4444'}
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                )}
                
                {/* Patrones detectados */}
                {candle.isPatternStart && (
                  <circle
                    cx={`${x}%`}
                    cy={closeY - 20}
                    r="3"
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
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-400 -ml-16">
          <span>{maxPrice.toFixed(4)}</span>
          <span>{((maxPrice + minPrice) / 2).toFixed(4)}</span>
          <span>{minPrice.toFixed(4)}</span>
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
          
          <div className="h-80 mb-4">
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