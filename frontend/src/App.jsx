import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  Background,
  ConnectionMode,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from '@xyflow/react'

import DevicePalette from './components/DevicePalette'
import NodePropertiesPanel from './components/NodePropertiesPanel'
import ImageImportModal from './components/ImageImportModal'
import ApplyPlanModal from './components/ApplyPlanModal'
import PlannedDeviceNode from './components/PlannedDeviceNode'

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


const NODE_TYPES = {
  plannedDevice: PlannedDeviceNode,
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
  runtimeMatch = null,
) {
  const fallbackPosition = {
    x: 300 + index * 30,
    y: 150 + index * 30,
  }


  const interfaceCount =
    desiredNode.properties?.interfaces ??
    device?.defaults?.interfaces ??
    device?.interfaces?.default ??
    1


  return {
    id: desiredNode.id,

    type: 'plannedDevice',

    position:
      position ||
      fallbackPosition,

    data: {
      name:
        desiredNode.name,

      templateName:
        device?.name ||
        desiredNode.template_id,

      kind:
        device?.kind ||
        'vm',

      runtime:
        device?.runtime,

      runtimeState:
        runtimeMatch?.state ||
        null,

      runtimeId:
        runtimeMatch?.id ||
        null,

      interfaceCount,

      interfacePrefix:
        device?.interfaces?.prefix ||
        'nic',
    },
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


function createPlannedEdge(
  link,
  reconciled = false,
) {
  const visiblePorts = [
    link.source_port,
    link.target_port,
  ].filter(
    (port) =>
      port &&
      !port.startsWith('network-')
  )


  return {
    id: link.id,

    source: link.source,
    target: link.target,

    sourceHandle:
      link.source_port || null,

    targetHandle:
      link.target_port || null,

    type: 'smoothstep',

    label:
      visiblePorts.join(' ↔ '),

    className:
      reconciled
        ? 'planned-edge reconciled-edge'
        : 'planned-edge',

    data: {
      reconciled,
    },
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
    showImageImport,
    setShowImageImport,
  ] = useState(false)


  const [
    showApplyPlan,
    setShowApplyPlan,
  ] = useState(false)


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
          applyPlanResponse,
        ] = await Promise.all([
          fetch('/api/lab/topology'),
          fetch('/api/lab/layout'),
          fetch('/api/catalog/devices'),
          fetch('/api/lab/desired'),
          fetch('/api/images'),
          fetch('/api/lab/apply-plan'),
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


        if (!applyPlanResponse.ok) {
          throw new Error(
            `Apply Plan API respondeu HTTP ${applyPlanResponse.status}`
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

        const applyPlan =
          await applyPlanResponse.json()


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


        const topologyNodeMap =
          Object.fromEntries(
            (topology.nodes || []).map(
              (node) => [
                node.id,
                node,
              ]
            )
          )


        const desiredNodeMap =
          Object.fromEntries(
            (desired.nodes || []).map(
              (node) => [
                node.id,
                node,
              ]
            )
          )


        const runtimeByDesiredId = {}

        const hiddenRealNodeIds =
          new Set()


        for (
          const action
          of applyPlan.actions || []
        ) {
          const desiredNode =
            desiredNodeMap[
              action.node_id
            ]


          let realNodeId = null


          if (action.domain_name) {
            realNodeId =
              `vm:${action.domain_name}`
          } else if (
            action.libvirt_network
          ) {
            realNodeId =
              `net:${action.libvirt_network}`
          }


          if (!realNodeId) {
            continue
          }


          const realNode =
            topologyNodeMap[
              realNodeId
            ]


          if (!realNode) {
            continue
          }


          runtimeByDesiredId[
            action.node_id
          ] = {
            id:
              realNode.id,

            state:
              realNode.state ||
              (
                realNode.active
                  ? 'active'
                  : null
              ),
          }


          /*
           * Cloud/NAT representa uma
           * rede compartilhada.
           *
           * A rede default continua
           * visivel como infraestrutura
           * real global.
           */
          if (
            desiredNode?.template_id
            !== 'cloud-nat'
          ) {
            hiddenRealNodeIds.add(
              realNodeId
            )
          }
        }


        const visibleRealTopologyNodes =
          (topology.nodes || []).filter(
            (node) =>
              !hiddenRealNodeIds.has(
                node.id
              )
          )


        const realNodes =
          visibleRealTopologyNodes.map(
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
                runtimeByDesiredId[
                  node.id
                ] || null,
              )
          )


        const visibleRealLinks =
          (topology.links || []).filter(
            (link) =>
              !hiddenRealNodeIds.has(
                link.source
              ) &&
              !hiddenRealNodeIds.has(
                link.target
              )
          )


        /*
         * Assinatura deterministica dos
         * links VM -> Network observados
         * no runtime.
         *
         * Exemplo:
         *
         * vm:ulab-fgt...|port1|net:default
         */
        const realVmNetworkLinks =
          new Set(
            (topology.links || [])
              .filter(
                (link) =>
                  link.type ===
                    'vm-network' &&
                  link.source &&
                  link.target &&
                  link.source_port
              )
              .map(
                (link) =>
                  [
                    link.source,
                    link.source_port,
                    link.target,
                  ].join('|')
              )
          )


        function isDesiredLinkReconciled(
          link,
        ) {
          const sourceRuntime =
            runtimeByDesiredId[
              link.source
            ]?.id

          const targetRuntime =
            runtimeByDesiredId[
              link.target
            ]?.id


          if (
            !sourceRuntime ||
            !targetRuntime
          ) {
            return false
          }


          let vmRuntime = null
          let networkRuntime = null
          let vmPort = null


          /*
           * Desired pode estar desenhado:
           *
           * Network -> VM
           *
           * ou:
           *
           * VM -> Network
           *
           * O topology real do libvirt
           * sempre representa VM -> Network.
           */
          if (
            sourceRuntime.startsWith(
              'vm:'
            ) &&
            targetRuntime.startsWith(
              'net:'
            )
          ) {
            vmRuntime =
              sourceRuntime

            networkRuntime =
              targetRuntime

            vmPort =
              link.source_port
          } else if (
            sourceRuntime.startsWith(
              'net:'
            ) &&
            targetRuntime.startsWith(
              'vm:'
            )
          ) {
            vmRuntime =
              targetRuntime

            networkRuntime =
              sourceRuntime

            vmPort =
              link.target_port
          } else {
            return false
          }


          if (
            !vmPort ||
            vmPort.startsWith(
              'network-'
            )
          ) {
            return false
          }


          const signature = [
            vmRuntime,
            vmPort,
            networkRuntime,
          ].join('|')


          return realVmNetworkLinks.has(
            signature
          )
        }


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

        setEdges([
          ...visibleRealLinks.map(
            createEdge
          ),

          ...(desired.links || []).map(
            (link) =>
              createPlannedEdge(
                link,
                isDesiredLinkReconciled(
                  link
                ),
              )
          ),
        ])
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

          setEdges(
            (currentEdges) =>
              currentEdges.filter(
                (edge) =>
                  edge.source !== nodeId &&
                  edge.target !== nodeId
              )
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


  const onConnect =
    useCallback(
      async (connection) => {
        if (
          !connection.source ||
          !connection.target ||
          !connection.sourceHandle ||
          !connection.targetHandle
        ) {
          return
        }


        if (
          connection.source ===
          connection.target
        ) {
          setSaveStatus(
            'Nao e permitido conectar o node nele mesmo'
          )

          return
        }


        const desiredNodes =
          desiredTopology.nodes || []

        const desiredLinks =
          desiredTopology.links || []


        const getDeviceForNode =
          (nodeId) => {
            const desiredNode =
              desiredNodes.find(
                (node) =>
                  node.id === nodeId
              )

            if (!desiredNode) {
              return null
            }

            return (
              catalogDevices.find(
                (device) =>
                  device.id ===
                  desiredNode.template_id
              ) || null
            )
          }


        const sourceDevice =
          getDeviceForNode(
            connection.source
          )

        const targetDevice =
          getDeviceForNode(
            connection.target
          )


        if (
          !sourceDevice ||
          !targetDevice
        ) {
          setSaveStatus(
            'Por enquanto conecte somente devices PLANNED'
          )

          return
        }


        const sharedKinds = [
          'network',
          'cloud',
        ]


        const handleIsUsed =
          (nodeId, handleId) =>
            desiredLinks.some(
              (link) =>
                (
                  link.source === nodeId &&
                  link.source_port === handleId
                ) ||
                (
                  link.target === nodeId &&
                  link.target_port === handleId
                )
            )


        if (
          !sharedKinds.includes(
            sourceDevice.kind
          ) &&
          handleIsUsed(
            connection.source,
            connection.sourceHandle,
          )
        ) {
          setSaveStatus(
            'Porta de origem ja esta conectada'
          )

          return
        }


        if (
          !sharedKinds.includes(
            targetDevice.kind
          ) &&
          handleIsUsed(
            connection.target,
            connection.targetHandle,
          )
        ) {
          setSaveStatus(
            'Porta de destino ja esta conectada'
          )

          return
        }


        const newLink = {
          id:
            `planned-link:${crypto.randomUUID()}`,

          source:
            connection.source,

          target:
            connection.target,

          source_port:
            connection.sourceHandle,

          target_port:
            connection.targetHandle,

          properties: {},
        }


        const updatedDesired = {
          ...desiredTopology,

          links: [
            ...desiredLinks,
            newLink,
          ],
        }


        setSaveStatus(
          'Salvando conexao...'
        )


        try {
          await saveDesiredTopology(
            updatedDesired
          )

          setDesiredTopology(
            updatedDesired
          )

          setEdges(
            (currentEdges) => [
              ...currentEdges,
              createPlannedEdge(
                newLink
              ),
            ]
          )

          setSaveStatus(
            'Conexao salva'
          )

          window.setTimeout(
            () =>
              setSaveStatus(''),
            1500,
          )
        } catch (err) {
          console.error(err)

          setSaveStatus(
            'Erro ao salvar conexao'
          )
        }
      },
      [
        desiredTopology,
        catalogDevices,
        saveDesiredTopology,
        setEdges,
      ]
    )


  const onEdgeDoubleClick =
    useCallback(
      async (_event, edge) => {
        const exists =
          (desiredTopology.links || [])
            .some(
              (link) =>
                link.id === edge.id
            )

        if (!exists) {
          return
        }


        const updatedDesired = {
          ...desiredTopology,

          links:
            (desiredTopology.links || [])
              .filter(
                (link) =>
                  link.id !== edge.id
              ),
        }


        try {
          await saveDesiredTopology(
            updatedDesired
          )

          setDesiredTopology(
            updatedDesired
          )

          setEdges(
            (currentEdges) =>
              currentEdges.filter(
                (item) =>
                  item.id !== edge.id
              )
          )

          setSaveStatus(
            'Conexao removida'
          )

          window.setTimeout(
            () =>
              setSaveStatus(''),
            1500,
          )
        } catch (err) {
          console.error(err)

          setSaveStatus(
            'Erro ao remover conexao'
          )
        }
      },
      [
        desiredTopology,
        saveDesiredTopology,
        setEdges,
      ]
    )


  const refreshImageLibrary =
    useCallback(
      async () => {
        const response =
          await fetch(
            '/api/images'
          )

        if (!response.ok) {
          throw new Error(
            `Images HTTP ${response.status}`
          )
        }

        const data =
          await response.json()

        setImageLibrary(
          data.images || []
        )
      },
      []
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
          <button
            type="button"
            className="apply-changes-button"
            onClick={() =>
              setShowApplyPlan(
                true
              )
            }
          >
            Apply Changes
          </button>


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

          onImportImage={() =>
            setShowImageImport(
              true
            )
          }
        />


        <main className="canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}

            nodeTypes={
              NODE_TYPES
            }

            connectionMode={
              ConnectionMode.Loose
            }

            onConnect={
              onConnect
            }

            onEdgeDoubleClick={
              onEdgeDoubleClick
            }

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


      {showApplyPlan && (
        <ApplyPlanModal
          onClose={() =>
            setShowApplyPlan(
              false
            )
          }
        />
      )}


      {showImageImport && (
        <ImageImportModal
          devices={
            catalogDevices
          }

          onClose={() =>
            setShowImageImport(
              false
            )
          }

          onImported={
            refreshImageLibrary
          }
        />
      )}
    </div>
  )
}


export default App
