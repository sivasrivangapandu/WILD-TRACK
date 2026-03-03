import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Home from './pages/Home';
import Upload from './pages/Upload';
import Dashboard from './pages/Dashboard';
import SpeciesExplorer from './pages/SpeciesExplorer';
import Compare from './pages/Compare';
import BatchProcess from './pages/BatchProcess';
import History from './pages/History';
import MapViewer from './pages/MapViewer';
import About from './pages/About';
import Chat from './pages/Chat';
import LoginPage from './pages/LoginPage';
import Settings from './pages/Settings';
import MLOps from './pages/MLOps';
import { AppStateProvider } from './context/AppStateContext';
import './styles/global.css';

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
      <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
      <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/species" element={<ProtectedRoute><SpeciesExplorer /></ProtectedRoute>} />
      <Route path="/compare" element={<ProtectedRoute><Compare /></ProtectedRoute>} />
      <Route path="/batch" element={<ProtectedRoute><BatchProcess /></ProtectedRoute>} />
      <Route path="/map" element={<ProtectedRoute><MapViewer /></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
      <Route path="/about" element={<ProtectedRoute><About /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
      <Route path="/mlops" element={<ProtectedRoute><MLOps /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AuthProvider>
          <AppStateProvider>
            <Layout>
              <AppRoutes />
            </Layout>
          </AppStateProvider>
        </AuthProvider>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
