import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    background: '#141414',
    primaryColor: '#1e1e1e',
    primaryTextColor: '#f0f0f0',
    primaryBorderColor: '#C5F135',
    lineColor: '#C5F135',
    secondaryColor: '#1a1a1a',
    tertiaryColor: '#222',
    edgeLabelBackground: '#141414',
    clusterBkg: '#1a1a1a',
    titleColor: '#f0f0f0',
    nodeBorder: '#C5F135',
    mainBkg: '#1e1e1e',
    nodeTextColor: '#f0f0f0',
  },
})

let counter = 0

export default function MermaidDiagram({ code }) {
  const ref = useRef(null)
  const [svg, setSvg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    const id = `mermaid-${++counter}`
    mermaid.render(id, code)
      .then(({ svg }) => setSvg(svg))
      .catch(e => setError(e.message || 'Diagram render error'))
  }, [code])

  if (error) return (
    <pre style={{ color: '#ff4444', fontSize: 11, background: '#1a0000', padding: '8px 12px', borderRadius: 6, overflowX: 'auto' }}>
      {error}
    </pre>
  )

  return (
    <div
      ref={ref}
      style={{ margin: '8px 0', background: '#0f0f0f', borderRadius: 8, padding: 16, border: '1px solid rgba(197,241,53,0.15)', overflowX: 'auto' }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}
