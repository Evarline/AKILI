/**
 * Entry point.
 *
 * Inter is self-hosted through @fontsource-variable, so the reference's
 * typography is matched without the browser fetching a font from a third-party
 * CDN.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import './styles/tokens.css'
import './styles/base.css'
import App from './App'

const container = document.getElementById('root')
if (!container) throw new Error('#root is missing from index.html')

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
