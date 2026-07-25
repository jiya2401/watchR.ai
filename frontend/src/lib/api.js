import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 15000 })

http.interceptors.response.use(
  r => r,
  err => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    return Promise.reject(new Error(msg))
  }
)

export const api = {
  // Companies
  listCompanies:  ()           => http.get('/companies/').then(r => r.data),
  addCompany:     (name)       => http.post(`/companies/?name=${encodeURIComponent(name)}`).then(r => r.data),
  deleteCompany:  (name)       => http.delete(`/companies/${encodeURIComponent(name)}`),
  getCompany:     (name)       => http.get(`/companies/${encodeURIComponent(name)}`).then(r => r.data),

  // Analysis
  triggerAnalysis: (company, force = false) =>
    http.post(`/analyze/${encodeURIComponent(company)}?force=${force}`).then(r => r.data),
  getReport:    (company) => http.get(`/analyze/${encodeURIComponent(company)}/report`).then(r => r.data),
  getAllReports: (company) => http.get(`/analyze/${encodeURIComponent(company)}/reports`).then(r => r.data),
  getStatus:    (company) => http.get(`/analyze/${encodeURIComponent(company)}/status`).then(r => r.data),

  // System
  health: () => axios.get('/health').then(r => r.data),
}
