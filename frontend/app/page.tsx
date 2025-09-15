'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@supabase/supabase-js'
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Activity, Clock, Target, AlertTriangle } from 'lucide-react'

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
}

export default function TradingDashboard() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [showAllStrategies, setShowAllStrategies] = useState(false)
  const [selectedTimeframe, setSelectedTimeframe] = useState('all')
  const [totalStrategies, setTotalStrategies] = useState(0)

  useEffect(() => {
    fetchStrategies()
  }, [])

  const fetchStrategies = async () => {
    try {
      const { data, error } = await supabase
        .from('forex_strategies')
        .select('*')
        .order('effectiveness', { ascending: false })
        .order('score', { ascending: false })

      if (error) {
        console.error('Error fetching strategies:', error)
        return
      }

      setStrategies(data || [])
      setTotalStrategies(data?.length || 0)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  // Filtrar estrategias por timeframe
  const filteredStrategies = selectedTimeframe === 'all'
    ? strategies
    : strategies.filter(s => s.timeframe === selectedTimeframe)

  // Top 5 estrategias más rentables
  const topStrategies = filteredStrategies.slice(0, 5)

  // Agrupar estrategias por timeframe para estadísticas
  const timeframeStats = strategies.reduce((acc, strategy) => {
    const tf = strategy.timeframe
    if (!acc[tf]) {
      acc[tf] = { count: 0, avgEffectiveness: 0, totalEffectiveness: 0 }
    }
    acc[tf].count++
    acc[tf].totalEffectiveness += strategy.effectiveness
    acc[tf].avgEffectiveness = acc[tf].totalEffectiveness / acc[tf].count
    return acc
  }, {} as Record<string, { count: number; avgEffectiveness: number; totalEffectiveness: number }>)

  const getEffectivenessColor = (effectiveness: number) => {
    if (effectiveness >= 90) return 'text-green-600 bg-green-100'
    if (effectiveness >= 80) return 'text-green-500 bg-green-50'
    if (effectiveness >= 70) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-500 bg-red-50'
  }

  const getDirectionIcon = (direction: string) => {
    return direction === 'CALL' ?
      <TrendingUp className="w-4 h-4 text-green-600" /> :
      <TrendingDown className="w-4 h-4 text-red-600" />
  }

  const getStrategyStatus = (effectiveness: number, score: number) => {
    if (effectiveness >= 85 && score >= 65) return { status: 'Excelente', color: 'text-green-700 bg-green-100' }
    if (effectiveness >= 75 && score >= 60) return { status: 'Buena', color: 'text-blue-700 bg-blue-100' }
    if (effectiveness >= 65 && score >= 55) return { status: 'Regular', color: 'text-yellow-700 bg-yellow-100' }
    return { status: 'Revisar', color: 'text-red-700 bg-red-100' }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white text-lg">Cargando estrategias de trading...</p>
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
            <div>
              <h1 className="text-3xl font-bold text-white">
                Sistema de Trading Automatizado
              </h1>
              <p className="text-gray-300 mt-1">
                Análisis de patrones y estrategias de Forex
              </p>
            </div>
            <div className="flex items-center space-x-6">
  <div className="text-right">
    <p className="text-sm text-gray-400">Última Actualización</p>
    <p className="text-lg text-blue-400">
      {strategies.length > 0
        ? new Date(Math.max(...strategies.map(s => new Date(s.analysis_date).getTime()))).toLocaleString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
          })
        : 'Cargando...'
      }
    </p>
  </div>
  <div className="text-right">
    <p className="text-sm text-gray-400">Total Estrategias</p>
    <p className="text-2xl font-bold text-green-400">{totalStrategies}</p>
  </div>
  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
</div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Estadísticas por Timeframe */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
          {Object.entries(timeframeStats).map(([timeframe, stats]) => (
            <div
              key={timeframe}
              className={`p-4 rounded-lg border transition-all cursor-pointer ${
                selectedTimeframe === timeframe
                  ? 'bg-purple-600/30 border-purple-400'
                  : 'bg-white/5 border-gray-600 hover:bg-white/10'
              }`}
              onClick={() => setSelectedTimeframe(selectedTimeframe === timeframe ? 'all' : timeframe)}
            >
              <div className="text-center">
                <Clock className="w-6 h-6 mx-auto mb-2 text-blue-400" />
                <p className="text-lg font-bold">{timeframe}</p>
                <p className="text-sm text-gray-400">{stats.count} estrategias</p>
                <p className="text-xs text-green-400">
                  {stats.avgEffectiveness.toFixed(1)}% avg
                </p>
              </div>
            </div>
          ))}
          <div
            className={`p-4 rounded-lg border transition-all cursor-pointer ${
              selectedTimeframe === 'all'
                ? 'bg-purple-600/30 border-purple-400'
                : 'bg-white/5 border-gray-600 hover:bg-white/10'
            }`}
            onClick={() => setSelectedTimeframe('all')}
          >
            <div className="text-center">
              <Activity className="w-6 h-6 mx-auto mb-2 text-green-400" />
              <p className="text-lg font-bold">TODAS</p>
              <p className="text-sm text-gray-400">{totalStrategies} total</p>
            </div>
          </div>
        </div>

        {/* TOP 5 Estrategias */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold flex items-center">
              <Target className="w-6 h-6 mr-2 text-yellow-400" />
              TOP 5 Estrategias Más Rentables
              {selectedTimeframe !== 'all' && (
                <span className="ml-2 text-lg text-blue-400">({selectedTimeframe})</span>
              )}
            </h2>
          </div>

          <div className="grid gap-4">
            {topStrategies.map((strategy, index) => {
              const status = getStrategyStatus(strategy.effectiveness, strategy.score)
              return (
                <div
                  key={strategy.id}
                  className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-gray-600 hover:border-gray-500 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full text-black font-bold text-lg">
                        #{index + 1}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="text-xl font-bold">{strategy.pair}</h3>
                          <span className="text-sm bg-blue-600 px-2 py-1 rounded">
                            {strategy.timeframe}
                          </span>
                          {getDirectionIcon(strategy.direction)}
                        </div>
                        <p className="text-gray-300">
                          Patrón: <span className="text-blue-400 font-mono">{strategy.pattern}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-6">
                      <div className="text-center">
                        <p className="text-sm text-gray-400">Efectividad</p>
                        <p className={`text-2xl font-bold ${getEffectivenessColor(strategy.effectiveness).split(' ')[0]}`}>
                          {strategy.effectiveness.toFixed(1)}%
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm text-gray-400">Score</p>
                        <p className="text-xl font-bold text-blue-400">
                          {strategy.score.toFixed(1)}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm text-gray-400">Operaciones</p>
                        <p className="text-lg">
                          <span className="text-green-400">{strategy.wins}</span> /
                          <span className="text-red-400">{strategy.losses}</span>
                        </p>
                      </div>
                      <div className="text-center">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${status.color}`}>
                          {status.status}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Botón para mostrar todas las estrategias */}
        <div className="text-center">
          <button
            onClick={() => setShowAllStrategies(!showAllStrategies)}
            className="bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded-lg font-medium transition-all flex items-center mx-auto space-x-2"
          >
            {showAllStrategies ? (
              <>
                <ChevronUp className="w-5 h-5" />
                <span>Ocultar Estrategias Completas</span>
              </>
            ) : (
              <>
                <ChevronDown className="w-5 h-5" />
                <span>Ver Todas las Estrategias ({filteredStrategies.length})</span>
              </>
            )}
          </button>
        </div>

        {/* Tabla completa de estrategias (colapsible) */}
        {showAllStrategies && (
          <div className="mt-8">
            <div className="bg-white/5 backdrop-blur-sm rounded-lg border border-gray-600 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-black/20">
                    <tr>
                      <th className="px-4 py-3 text-left">Par</th>
                      <th className="px-4 py-3 text-left">Timeframe</th>
                      <th className="px-4 py-3 text-left">Patrón</th>
                      <th className="px-4 py-3 text-left">Dirección</th>
                      <th className="px-4 py-3 text-right">Efectividad</th>
                      <th className="px-4 py-3 text-right">Score</th>
                      <th className="px-4 py-3 text-right">Wins/Losses</th>
                      <th className="px-4 py-3 text-center">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {filteredStrategies.map((strategy) => {
                      const status = getStrategyStatus(strategy.effectiveness, strategy.score)
                      return (
                        <tr key={strategy.id} className="hover:bg-white/5">
                          <td className="px-4 py-3 font-medium">{strategy.pair}</td>
                          <td className="px-4 py-3">
                            <span className="bg-blue-600 px-2 py-1 rounded text-xs">
                              {strategy.timeframe}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-blue-400">{strategy.pattern}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-center space-x-1">
                              {getDirectionIcon(strategy.direction)}
                              <span>{strategy.direction}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={`font-bold ${getEffectivenessColor(strategy.effectiveness).split(' ')[0]}`}>
                              {strategy.effectiveness.toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-medium">
                            {strategy.score.toFixed(1)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-green-400">{strategy.wins}</span> /
                            <span className="text-red-400">{strategy.losses}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${status.color}`}>
                              {status.status}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}