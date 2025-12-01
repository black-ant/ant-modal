import React from 'react'
import {createRoot} from 'react-dom/client'
import './index.css'
import App from './App'
import { LogProvider } from './context/LogContext'

const container = document.getElementById('root')

const root = createRoot(container!)

root.render(
    <React.StrictMode>
        <LogProvider>
            <App/>
        </LogProvider>
    </React.StrictMode>
)
