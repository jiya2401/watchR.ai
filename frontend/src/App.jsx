import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import LiveAgent from './pages/LiveAgent'
import Report from './pages/Report'

export default function App() {
  return (
    <Routes>
      <Route path="/"                          element={<Home />} />
      <Route path="/live/:company/:jobId"      element={<LiveAgent />} />
      <Route path="/report/:company"           element={<Report />} />
    </Routes>
  )
}
