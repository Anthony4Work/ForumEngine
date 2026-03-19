import service, { requestWithRetry } from './index'

/**
 * Create deliberation
 * @param {Object} data - { project_id, graph_id? }
 */
export const createSimulation = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/create', data), 3, 1000)
}

/**
 * Prepare deliberation environment (async task)
 * @param {Object} data - { simulation_id, entity_types?, use_llm_for_profiles?, force_regenerate? }
 */
export const prepareSimulation = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/prepare', data), 3, 1000)
}

/**
 * Query preparation task progress
 * @param {Object} data - { task_id?, simulation_id? }
 */
export const getPrepareStatus = (data) => {
  return service.post('/api/simulation/prepare/status', data)
}

/**
 * Get deliberation state
 * @param {string} simulationId
 */
export const getSimulation = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}`)
}

/**
 * Get tactical agent profiles
 * @param {string} simulationId
 */
export const getSimulationProfiles = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/profiles`)
}

/**
 * Get agent profiles in real-time during generation
 * @param {string} simulationId
 */
export const getSimulationProfilesRealtime = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/profiles/realtime`)
}

/**
 * Get deliberation configuration
 * @param {string} simulationId
 */
export const getSimulationConfig = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config`)
}

/**
 * Get config in real-time during generation
 * @param {string} simulationId
 */
export const getSimulationConfigRealtime = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config/realtime`)
}

/**
 * List all deliberations
 * @param {string} projectId - Optional, filter by project ID
 */
export const listSimulations = (projectId) => {
  const params = projectId ? { project_id: projectId } : {}
  return service.get('/api/simulation/list', { params })
}

/**
 * Start tactical deliberation
 * @param {Object} data - { simulation_id, max_rounds?, enable_graph_memory_update?, graph_id? }
 */
export const startSimulation = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/start', data), 3, 1000)
}

/**
 * Stop deliberation
 * @param {Object} data - { simulation_id }
 */
export const stopSimulation = (data) => {
  return service.post('/api/simulation/stop', data)
}

/**
 * Get deliberation run status
 * @param {string} simulationId
 */
export const getRunStatus = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status`)
}

/**
 * Get detailed run status (includes recent actions)
 * @param {string} simulationId
 */
export const getRunStatusDetail = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status/detail`)
}

/**
 * Get deliberation actions (replaces posts endpoint)
 * @param {string} simulationId
 * @param {number} limit
 * @param {number} offset
 */
export const getSimulationPosts = (simulationId, platform = 'deliberation', limit = 50, offset = 0) => {
  return service.get(`/api/simulation/${simulationId}/posts`, {
    params: { limit, offset }
  })
}

/**
 * Get deliberation timeline (grouped by phase)
 * @param {string} simulationId
 */
export const getSimulationTimeline = (simulationId, startRound = 0, endRound = null) => {
  const params = { start_round: startRound }
  if (endRound !== null) {
    params.end_round = endRound
  }
  return service.get(`/api/simulation/${simulationId}/timeline`, { params })
}

/**
 * Get per-agent statistics
 * @param {string} simulationId
 */
export const getAgentStats = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/agent-stats`)
}

/**
 * Get deliberation action history
 * @param {string} simulationId
 * @param {Object} params - { limit, offset, agent_id, phase, round_num }
 */
export const getSimulationActions = (simulationId, params = {}) => {
  return service.get(`/api/simulation/${simulationId}/actions`, { params })
}

/**
 * Close deliberation environment gracefully
 * @param {Object} data - { simulation_id, timeout? }
 */
export const closeSimulationEnv = (data) => {
  return service.post('/api/simulation/close-env', data)
}

/**
 * Get deliberation environment status
 * @param {Object} data - { simulation_id }
 */
export const getEnvStatus = (data) => {
  return service.post('/api/simulation/env-status', data)
}

/**
 * Batch interview tactical agents
 * @param {Object} data - { simulation_id, interviews: [{ agent_id, prompt }] }
 */
export const interviewAgents = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/interview/batch', data), 3, 1000)
}

/**
 * Get simulation history (with project details)
 * @param {number} limit
 */
export const getSimulationHistory = (limit = 20) => {
  return service.get('/api/simulation/history', { params: { limit } })
}
