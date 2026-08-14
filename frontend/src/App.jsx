import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from '@xyflow/react'

import DevicePalette from './components/DevicePalette'
import NodePropertiesPanel from './components/NodePropertiesPanel'

import '@xyflow/react/dist/style.css'
import './App.css'


const DEFAULT_POSITIONS = {
  'net:default': {
    x: 390,
    y: 20,
  },

  'vm:FGT-DC-A': {
    x: 130,
    y: 180,
  },

  'net:UNDERLAY': {
    x: 400,
    y: 195,
  },

  'vm:FGT-DC-B': {
    x: 670,
    y: 180,
  },

  'net:LAN-DC-A': {
    x: 145,
    y: 370,
  },

  'net:LAN-DC-B': {
    x: 685,
    y: 370,
  },

  'host:HOST-A': {
    x: 145,
    y: 540,
  },

  'host:HOST-B': {
    x: 685,
    y: 540,
  },
}


function createRealNode(
  node,
  index,
  savedPositions,
) {
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

    className:
      `lab-node lab-node-${node.type}`,
  }
}


function createPlannedNode(
  desiredNode,
  device,
  index,
  position,
) {
  const fallbackPosition = {
    x: 300 + index * 30,
    y: 150 + index * 30,
  }


  return {
    id: desiredNode.id,

    position:
      position ||
      fallbackPosition,

    data: {
      label: (
        <div className="node-content">
          <div className="node-planned-state">
            PLANNED
          </div>

          <strong>
            {desiredNode.name}
          </strong>

          <span>
            {device?.name ||
              desiredNode.template_id}
          </span>
        </div>
      ),
    },

    className:
      'lab-node lab-node-planned',
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


function createPlannedName(
  device,
  desiredNodes,
) {
  const count =
    desiredNodes.filter(
      (node) =>
        node.template_id === device.id
    ).length + 1

  return `${device.name} ${count}`
}


function App() {
  const [
    nodes,
    setNodes,
    onNodesChange,
  ] = useNodesState([])


  const [
    edges,
    setEdges,
    onEdgesChange,
  ] = useEdgesState([])


  const [
    reactFlowInstance,
    setReactFlowInstance,
  ] = useState(null)


  const [
    catalogDevices,
    setCatalogDevices,
  ] = useState([])


  const [
    imageLibrary,
    setImageLibrary,
  ] = useState([])


  const [
    desiredTopology,
    setDesiredTopology,
  ] = useState({
    schema_version: 1,
    nodes: [],
    links: [],
  })


  const [
    selectedDesiredNodeId,
    setSelectedDesiredNodeId,
  ] = useState(null)


  const [labInfo, setLabInfo] =
    useState(null)


  const [loading, setLoading] =
    useState(true)


  const [error, setError] =
    useState(null)


  const [
    saveStatus,
    setSaveStatus,
  ] = useState('')


  useEffect(() => {
    async function loadLab() {
      try {
        const [
          topologyResponse,
          layoutResponse,
          catalogResponse,
          desiredResponse,
          imagesResponse,
        ] = await Promise.all([
          fetch('/api/lab/topology'),
          fetch('/api/lab/layout'),
          fetch('/api/catalog/devices'),
          fetch('/api/lab/desired'),
          fetch('/api/images'),
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


        if (!catalogResponse.ok) {
          throw new Error(
            `Catalog API respondeu HTTP ${catalogResponse.status}`
          )
        }


        if (!desiredResponse.ok) {
          throw new Error(
            `Desired API respondeu HTTP ${desiredResponse.status}`
          )
        }


        if (!imagesResponse.ok) {
          throw new Error(
            `Images API respondeu HTTP ${imagesResponse.status}`
          )
        }


        const topology =
          await topologyResponse.json()

        const layout =
          await layoutResponse.json()

        const catalog =
          await catalogResponse.json()

        const desired =
          await desiredResponse.json()

        const images =
          await imagesResponse.json()


        const savedPositions = {}

        for (
          const node
          of layout.nodes || []
        ) {
          savedPositions[node.id] =
            node.position
        }


        const catalogMap =
          Object.fromEntries(
            (catalog.devices || []).map(
              (device) => [
                device.id,
                device,
              ]
            )
          )


        const realNodes =
          topology.nodes.map(
            (node, index) =>
              createRealNode(
                node,
                index,
                savedPositions,
              )
          )


        const plannedNodes =
          (desired.nodes || []).map(
            (node, index) =>
              createPlannedNode(
                node,
                catalogMap[
                  node.template_id
                ],
                index,
                savedPositions[node.id],
              )
          )


        setLabInfo(topology)

        setCatalogDevices(
          catalog.devices || []
        )

        setImageLibrary(
          images.images || []
        )

        setDesiredTopology(
          desired
        )

        setNodes([
          ...realNodes,
          ...plannedNodes,
        ])

        setEdges(
          topology.links.map(
            createEdge
          )
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


      const response =
        await fetch(
          '/api/lab/layout',
          {
            method: 'PUT',

            headers: {
              'Content-Type':
                'application/json',
            },

            body:
              JSON.stringify(
                payload
              ),
          }
        )


      if (!response.ok) {
        throw new Error(
          `Layout HTTP ${response.status}`
        )
      }
    },
    []
  )


  const saveDesiredTopology =
    useCallback(
      async (topology) => {
        const response =
          await fetch(
            '/api/lab/desired',
            {
              method: 'PUT',

              headers: {
                'Content-Type':
                  'application/json',
              },

              body:
                JSON.stringify(
                  topology
                ),
            }
          )


        if (!response.ok) {
          throw new Error(
            `Desired HTTP ${response.status}`
          )
        }


        return response.json()
      },
      []
    )


  const selectedDesiredNode =
    desiredTopology.nodes?.find(
      (node) =>
        node.id ===
        selectedDesiredNodeId
    ) || null


  const selectedDevice =
    catalogDevices.find(
      (device) =>
        device.id ===
        selectedDesiredNode?.template_id
    ) || null


  const onNodeClick =
    useCallback(
      (_event, node) => {
        if (
          node.id.startsWith(
            'planned:'
          )
        ) {
          setSelectedDesiredNodeId(
            node.id
          )

          return
        }

        setSelectedDesiredNodeId(
          null
        )
      },
      []
    )


  const updateDesiredNode =
    useCallback(
      async (updatedNode) => {
        const updatedDesired = {
          ...desiredTopology,

          nodes:
            desiredTopology.nodes.map(
              (node) =>
                node.id ===
                updatedNode.id
                  ? updatedNode
                  : node
            ),
        }


        setSaveStatus(
          'Salvando propriedades...'
        )


        try {
          await saveDesiredTopology(
            updatedDesired
          )

          setDesiredTopology(
            updatedDesired
          )


          const device =
            catalogDevices.find(
              (item) =>
                item.id ===
                updatedNode.template_id
            )


          setNodes(
            (currentNodes) =>
              currentNodes.map(
                (flowNode) => {
                  if (
                    flowNode.id !==
                    updatedNode.id
                  ) {
                    return flowNode
                  }

                  return createPlannedNode(
                    updatedNode,
                    device,
                    0,
                    flowNode.position,
                  )
                }
              )
          )


          setSaveStatus(
            'Propriedades salvas'
          )

          window.setTimeout(
            () =>
              setSaveStatus(''),
            1600,
          )
        } catch (err) {
          console.error(err)

          setSaveStatus(
            'Erro ao salvar propriedades'
          )
        }
      },
      [
        desiredTopology,
        catalogDevices,
        saveDesiredTopology,
        setNodes,
      ]
    )


  const deleteDesiredNode =
    useCallback(
      async (nodeId) => {
        const updatedDesired = {
          ...desiredTopology,

          nodes:
            desiredTopology.nodes.filter(
              (node) =>
                node.id !== nodeId
            ),

          links:
            (desiredTopology.links || [])
              .filter(
                (link) =>
                  link.source !== nodeId &&
                  link.target !== nodeId
              ),
        }


        const updatedNodes =
          nodes.filter(
            (node) =>
              node.id !== nodeId
          )


        setSaveStatus(
          'Removendo device...'
        )


        try {
          await saveDesiredTopology(
            updatedDesired
          )

          await saveLayout(
            updatedNodes
          )

          setDesiredTopology(
            updatedDesired
          )

          setNodes(
            updatedNodes
          )

          setSelectedDesiredNodeId(
            null
          )

          setSaveStatus(
            'Device removido'
          )

          window.setTimeout(
            () =>
              setSaveStatus(''),
            1500,
          )
        } catch (err) {
          console.error(err)

          setSaveStatus(
            'Erro ao remover device'
          )
        }
      },
      [
        desiredTopology,
        nodes,
        saveDesiredTopology,
        saveLayout,
        setNodes,
      ]
    )


  const onNodeDragStop =
    useCallback(
      async (
        _event,
        draggedNode,
      ) => {
        const updatedNodes =
          nodes.map((node) => {
            if (
              node.id !==
              draggedNode.id
            ) {
              return node
            }

            return {
              ...node,

              position:
                draggedNode.position,
            }
          })


        setNodes(
          updatedNodes
        )

        setSaveStatus(
          'Salvando layout...'
        )


        try {
          await saveLayout(
            updatedNodes
          )

          setSaveStatus(
            'Layout salvo'
          )

          window.setTimeout(
            () =>
              setSaveStatus(''),
            1500,
          )
        } catch (err) {
          console.error(err)

          setSaveStatus(
            'Erro ao salvar layout'
          )
        }
      },
      [
        nodes,
        setNodes,
        saveLayout,
      ]
    )


  const onDragOver =
    useCallback((event) => {
      event.preventDefault()

      event.dataTransfer.dropEffect =
        'copy'
    }, [])


  const onDrop =
    useCallback(
      async (event) => {
        event.preventDefault()


        if (!reactFlowInstance) {
          return
        }


        const rawData =
          event.dataTransfer.getData(
            'application/unidac-device'
          )


        if (!rawData) {
          return
        }


        let dragData

        try {
          dragData =
            JSON.parse(rawData)
        } catch {
          return
        }


        const device =
          catalogDevices.find(
            (item) =>
              item.id ===
              dragData.template_id
          )


        if (!device) {
          return
        }


        const position =
          reactFlowInstance
            .screenToFlowPosition({
              x: event.clientX,
              y: event.clientY,
            })


        const desiredNodes =
          desiredTopology.nodes || []


        const nodeId =
          `planned:${crypto.randomUUID()}`


        const newDesiredNode = {
          id: nodeId,

          template_id:
            device.id,

          name:
            createPlannedName(
              device,
              desiredNodes,
            ),

          state: 'planned',

          properties: {},
        }


        const updatedDesired = {
          ...desiredTopology,

          nodes: [
            ...desiredNodes,
            newDesiredNode,
          ],
        }


        const newFlowNode =
          createPlannedNode(
            newDesiredNode,
            device,
            desiredNodes.length,
            position,
          )


        const updatedNodes = [
          ...nodes,
          newFlowNode,
        ]


        setSaveStatus(
          'Salvando device...'
        )


        try {
          await saveDesiredTopology(
            updatedDesired
          )

          await saveLayout(
            updatedNodes
          )


          setDesiredTopology(
            updatedDesired
          )

          setNodes(
            updatedNodes
          )

          setSelectedDesiredNodeId(
            nodeId
          )


          setSaveStatus(
            'Device planejado salvo'
          )


          window.setTimeout(
            () =>
              setSaveStatus(''),
            1800,
          )
        } catch (err) {
          console.error(err)

          setSaveStatus(
            'Erro ao salvar device'
          )
        }
      },
      [
        reactFlowInstance,
        catalogDevices,
        desiredTopology,
        nodes,
        setNodes,
        saveDesiredTopology,
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
        Erro ao carregar:
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


      <div className="workspace">
        <DevicePalette
          devices={catalogDevices}
        />


        <main className="canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}

            onInit={
              setReactFlowInstance
            }

            onNodesChange={
              onNodesChange
            }

            onEdgesChange={
              onEdgesChange
            }

            onNodeDragStop={
              onNodeDragStop
            }

            onNodeClick={
              onNodeClick
            }

            onDragOver={
              onDragOver
            }

            onDrop={
              onDrop
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


        {selectedDesiredNode && (
          <NodePropertiesPanel
            node={
              selectedDesiredNode
            }

            device={
              selectedDevice
            }

            images={
              imageLibrary
            }

            onClose={() =>
              setSelectedDesiredNodeId(
                null
              )
            }

            onSave={
              updateDesiredNode
            }

            onDelete={
              deleteDesiredNode
            }
          />
        )}
      </div>
    </div>
  )
}


export default App
