/**
 * Temporary storage for pending upload files and requirements
 * Used for immediate navigation after clicking start on the home page, with API calls made on the Process page
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  domainHints: '',
  isPending: false
})

export function setPendingUpload(files, requirement, domainHints = '') {
  state.files = files
  state.simulationRequirement = requirement
  state.domainHints = domainHints
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    domainHints: state.domainHints,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.domainHints = ''
  state.isPending = false
}

export default state
