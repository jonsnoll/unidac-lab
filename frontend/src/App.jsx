import { useCallback, useEffect, useState } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from '@xyflow/react'

import '@xyflow/react/dist/style.css'
import './App.css'


const DEFAULT_POSITIONS = {
  'net:default': { x: 390, y: 20 },

  'vm:FGT-DC-A': { x: 130, y: 180 },
  'net:UNDERLAY': { x: 400, y: 195 },
  'vm:FGT-DC-B': { x: 670, y: 180 },

  'net:LAN-DC-A': { x: 145, y: 370 },
  'net:LAN-DC-B': { x: 685, y: 370 },

  'host:HOST-A': { x: 145, y: 540 },
  'host:HOST-B': { x: 685, y: 540 },
}


function createNode(node, index, savedPositions) {
  const position =
    savedPositions[node.id] ||
    DEFAULT_POSITIONS[node.id] || {
      x: 100 + index * 180,
      y: 650,
    }

  let subtitle = ''

  if (node.type === 'vm') {
    subtitle = node.state
  }

  if (node.type === 'network') {
    subtitle = node.bridge
  }

  if (node.type === 'host') {
    subtitle = node.state
  }

  return {
    id: node.id,
    position,

    data: {
      label: (
        <div className="node-content">
          <div className="node-type">
            {node.type}
          </div>

          <strong>
            {node.name}
          </strong>

          <span>
            {subtitle}
          </span>
        </div>
      ),
    },

    className: `lab-node lab-node-${node.type}`,
  }
}


function createEdge(link) {
  return {
    id: link.id,
    source: link.source,
    target: link.target,
    type: 'smoothstep',

    label:
      link.source_port ||
      link.details?.host_interface ||
      '',

    animated:
      link.target === 'net:UNDERLAY',

    className:
      link.target === 'net:UNDERLAY'
        ? 'underlay-edge'
        : '',
  }
}


function App() {
  const [nodes, setNodes, onNodesChange] =
    useNodesState([])

  const [edges, setEdges, onEdgesChange] =
    useEdgesState([])

  const [labInfo, setLabInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saveStatus, setSaveStatus] = useState('')


  useEffect(() => {
    async function loadLab() {
      try {
        const [
          topologyResponse,
          layoutResponse,
        ] = await Promise.all([
          fetch('/api/lab/topology'),
          fetch('/api/lab/layout'),
        ])

        if (!topologyResponse.ok) {
          throw new Error(
            `Topology API respondeu HTTP ${topologyResponse.status}`
          )
        }

        if (!layoutResponse.ok) {
          throw new Error(
            `Layout API respondeu HTTP ${layoutResponse.status}`
          )
        }

        const topology =
          await topologyResponse.json()

        const layout =
          await layoutResponse.json()

        const savedPositions = {}

        for (const node of layout.nodes || []) {
          savedPositions[node.id] =
            node.position
        }

        setLabInfo(topology)

        setNodes(
          topology.nodes.map(
            (node, index) =>
              createNode(
                node,
                index,
                savedPositions,
              )
          )
        )

        setEdges(
          topology.links.map(createEdge)
        )
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadLab()
  }, [setNodes, setEdges])


  const saveLayout = useCallback(
    async (currentNodes) => {
      const payload = {
        nodes: currentNodes.map(
          (node) => ({
            id: node.id,

            position: {
              x: node.position.x,
              y: node.position.y,
            },
          })
        ),
      }

      setSaveStatus('Salvando...')

      try {
        const response = await fetch(
          '/api/lab/layout',
          {
            method: 'PUT',

            headers: {
              'Content-Type':
                'application/json',
            },

            body: JSON.stringify(payload),
          }
        )

        if (!response.ok) {
          throw new Error(
            `HTTP ${response.status}`
          )
        }

        setSaveStatus('Layout salvo')

        window.setTimeout(
          () => setSaveStatus(''),
          1500,
        )
      } catch (err) {
        console.error(
          'Erro ao salvar layout:',
          err,
        )

        setSaveStatus(
          'Erro ao salvar layout'
        )
      }
    },
    []
  )


  const onNodeDragStop = useCallback(
    (_event, draggedNode) => {
      const updatedNodes =
        nodes.map((node) => {
          if (node.id !== draggedNode.id) {
            return node
          }

          return {
            ...node,
            position: draggedNode.position,
          }
        })

      setNodes(updatedNodes)
      saveLayout(updatedNodes)
    },
    [
      nodes,
      setNodes,
      saveLayout,
    ]
  )


  if (loading) {
    return (
      <div className="message-screen">
        Carregando laboratório...
      </div>
    )
  }


  if (error) {
    return (
      <div className="message-screen error">
        Erro ao carregar topologia:
        <br />
        {error}
      </div>
    )
  }


  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>
            unidac-lab
          </h1>

          <span>
            Network Lab Platform
          </span>
        </div>

        <div className="lab-status">
          {saveStatus && (
            <span className="save-status">
              {saveStatus}
            </span>
          )}

          <span className="status-dot" />

          {labInfo?.lab}
        </div>
      </header>


      <main className="canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}

          onNodesChange={
            onNodesChange
          }

          onEdgesChange={
            onEdgesChange
          }

          onNodeDragStop={
            onNodeDragStop
          }

          fitView

          fitViewOptions={{
            padding: 0.2,
          }}
        >
          <Background
            gap={24}
            size={1}
          />

          <MiniMap
            pannable
            zoomable
          />

          <Controls />
        </ReactFlow>
      </main>
    </div>
  )
}


export default App
