import {
  useEffect,
  useState,
} from 'react'

import './LinkCaptureModal.css'


function errorMessage(data) {
  return (
    data?.detail?.message ||
    data?.message ||
    'Operation failed.'
  )
}


function formatBytes(bytes) {
  if (!bytes) {
    return '0 B'
  }

  if (bytes >= 1024 * 1024) {
    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(1)} MiB`
  }

  if (bytes >= 1024) {
    return `${(
      bytes / 1024
    ).toFixed(1)} KiB`
  }

  return `${bytes} B`
}


function formatPacketTime(value) {
  const number = Number(value)

  if (!Number.isFinite(number)) {
    return '-'
  }

  return number.toFixed(6)
}


function LinkCaptureModal({
  link,
  onClose,
}) {
  const [captureId, setCaptureId] =
    useState(null)

  const [status, setStatus] =
    useState('ready')

  const [sizeBytes, setSizeBytes] =
    useState(0)

  const [
    runtimeInterface,
    setRuntimeInterface,
  ] = useState('')

  const [error, setError] =
    useState('')

  const [
    previewPackets,
    setPreviewPackets,
  ] = useState([])

  const [
    previewStatus,
    setPreviewStatus,
  ] = useState('idle')

  const [
    previewError,
    setPreviewError,
  ] = useState('')

  const [
    previewReturned,
    setPreviewReturned,
  ] = useState(0)

  const [
    previewTruncated,
    setPreviewTruncated,
  ] = useState(false)

  const [
    previewLimit,
    setPreviewLimit,
  ] = useState(100)


  const [delayMs, setDelayMs] =
    useState(0)

  const [jitterMs, setJitterMs] =
    useState(0)

  const [lossPct, setLossPct] =
    useState(0)

  const [rateMbit, setRateMbit] =
    useState(0)

  const [
    impairmentActive,
    setImpairmentActive,
  ] = useState(false)

  const [
    impairmentRaw,
    setImpairmentRaw,
  ] = useState('')

  const [
    impairmentBusy,
    setImpairmentBusy,
  ] = useState(false)


  useEffect(() => {
    async function loadImpairment() {
      try {
        const response = await fetch(
          `/api/lab/links/${
            encodeURIComponent(
              link.linkId
            )
          }/impairment`
        )

        const data =
          await response.json()

        if (!response.ok) {
          return
        }

        setImpairmentActive(
          Boolean(
            data.result?.enabled
          )
        )

        setImpairmentRaw(
          data.result?.qdisc ||
          ''
        )

      } catch {
        // Link tools can still open.
      }
    }

    loadImpairment()
  }, [
    link.linkId,
  ])


  useEffect(() => {
    if (
      !captureId ||
      status !== 'running'
    ) {
      return undefined
    }

    const interval =
      window.setInterval(
        async () => {
          try {
            const response =
              await fetch(
                `/api/lab/captures/${
                  encodeURIComponent(
                    captureId
                  )
                }`
              )

            const data =
              await response.json()

            if (!response.ok) {
              return
            }

            setSizeBytes(
              data.result
                ?.size_bytes ||
              0
            )

            if (
              data.result?.status
              !== 'running'
            ) {
              const nextStatus =
                data.result
                  ?.status ||
                'finished'

              setStatus(
                nextStatus
              )

              if (
                [
                  'stopped',
                  'finished',
                ].includes(
                  nextStatus
                )
              ) {
                loadPreview(
                  captureId
                )
              }
            }

          } catch {
            // Keep current state.
          }
        },
        1000,
      )

    return () => {
      window.clearInterval(
        interval
      )
    }
  }, [
    captureId,
    status,
  ])


  async function loadPreview(
    targetCaptureId = captureId,
  ) {
    if (!targetCaptureId) {
      return
    }

    setPreviewStatus('loading')
    setPreviewError('')

    try {
      const response = await fetch(
        `/api/lab/captures/${
          encodeURIComponent(
            targetCaptureId
          )
        }/preview?limit=${
          encodeURIComponent(
            previewLimit
          )
        }`
      )

      const data =
        await response.json()

      if (!response.ok) {
        throw new Error(
          errorMessage(data)
        )
      }

      const packets =
        Array.isArray(
          data.packets
        )
          ? data.packets
          : []

      setPreviewPackets(
        packets
      )

      setPreviewReturned(
        Number(
          data.returned ||
          packets.length
        )
      )

      setPreviewTruncated(
        Boolean(
          data.truncated
        )
      )

      setPreviewStatus(
        'ready'
      )

    } catch (err) {
      setPreviewPackets([])
      setPreviewReturned(0)
      setPreviewTruncated(false)
      setPreviewStatus('error')
      setPreviewError(
        err.message
      )
    }
  }


  async function startCapture() {
    setError('')
    setStatus('starting')

    setPreviewPackets([])
    setPreviewStatus('idle')
    setPreviewError('')
    setPreviewReturned(0)
    setPreviewTruncated(false)

    try {
      const response = await fetch(
        `/api/lab/links/${
          encodeURIComponent(
            link.linkId
          )
        }/capture/start`,
        {
          method: 'POST',
        }
      )

      const data =
        await response.json()

      if (!response.ok) {
        throw new Error(
          errorMessage(data)
        )
      }

      setCaptureId(
        data.capture_id
      )

      setRuntimeInterface(
        data.result
          ?.interface ||
        ''
      )

      setSizeBytes(
        data.result
          ?.size_bytes ||
        0
      )

      setStatus('running')

    } catch (err) {
      setStatus('ready')
      setError(err.message)
    }
  }


  async function stopCapture() {
    if (!captureId) {
      return
    }

    setError('')
    setStatus('stopping')

    try {
      const response = await fetch(
        `/api/lab/captures/${
          encodeURIComponent(
            captureId
          )
        }/stop`,
        {
          method: 'POST',
        }
      )

      const data =
        await response.json()

      if (!response.ok) {
        throw new Error(
          errorMessage(data)
        )
      }

      setSizeBytes(
        data.result
          ?.size_bytes ||
        0
      )

      const nextStatus =
        data.result?.status ||
        'finished'

      setStatus(
        nextStatus
      )

      if (
        [
          'stopped',
          'finished',
        ].includes(
          nextStatus
        )
      ) {
        await loadPreview(
          captureId
        )
      }

    } catch (err) {
      setStatus('running')
      setError(err.message)
    }
  }


  function downloadCapture() {
    if (!captureId) {
      return
    }

    window.open(
      `/api/lab/captures/${
        encodeURIComponent(
          captureId
        )
      }/download`,
      '_blank',
    )
  }


  async function applyImpairment() {
    setError('')
    setImpairmentBusy(true)

    try {
      const response = await fetch(
        `/api/lab/links/${
          encodeURIComponent(
            link.linkId
          )
        }/impairment`,
        {
          method: 'POST',

          headers: {
            'Content-Type':
              'application/json',
          },

          body: JSON.stringify({
            delay_ms:
              Number(delayMs),

            jitter_ms:
              Number(jitterMs),

            loss_pct:
              Number(lossPct),

            rate_mbit:
              Number(rateMbit),
          }),
        }
      )

      const data =
        await response.json()

      if (!response.ok) {
        throw new Error(
          errorMessage(data)
        )
      }

      setImpairmentActive(
        Boolean(
          data.result?.enabled
        )
      )

      setImpairmentRaw(
        data.result?.qdisc ||
        ''
      )

    } catch (err) {
      setError(err.message)

    } finally {
      setImpairmentBusy(false)
    }
  }


  async function clearImpairment() {
    setError('')
    setImpairmentBusy(true)

    try {
      const response = await fetch(
        `/api/lab/links/${
          encodeURIComponent(
            link.linkId
          )
        }/impairment`,
        {
          method: 'DELETE',
        }
      )

      const data =
        await response.json()

      if (!response.ok) {
        throw new Error(
          errorMessage(data)
        )
      }

      setDelayMs(0)
      setJitterMs(0)
      setLossPct(0)
      setRateMbit(0)

      setImpairmentActive(false)

      setImpairmentRaw(
        data.result?.qdisc ||
        ''
      )

    } catch (err) {
      setError(err.message)

    } finally {
      setImpairmentBusy(false)
    }
  }


  const finished = [
    'stopped',
    'finished',
  ].includes(status)


  return (
    <div className="capture-overlay">
      <div className="capture-modal link-tools-modal">
        <div className="capture-header">
          <div>
            <strong>
              Link Tools
            </strong>

            <span>
              {link.sourceName}
              {' ↔ '}
              {link.targetName}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
          >
            ×
          </button>
        </div>


        <div className="capture-body">
          <section className="link-tool-section">
            <h3>
              Network Impairment
            </h3>

            <div className="impairment-status">
              <span>
                Status
              </span>

              <strong
                className={
                  impairmentActive
                    ? 'active'
                    : ''
                }
              >
                {
                  impairmentActive
                    ? 'ACTIVE'
                    : 'CLEAR'
                }
              </strong>
            </div>


            <div className="impairment-grid">
              <label>
                Delay (ms)

                <input
                  type="number"
                  min="0"
                  max="5000"
                  value={delayMs}
                  onChange={(event) =>
                    setDelayMs(
                      event.target.value
                    )
                  }
                />
              </label>


              <label>
                Jitter (ms)

                <input
                  type="number"
                  min="0"
                  max="5000"
                  value={jitterMs}
                  onChange={(event) =>
                    setJitterMs(
                      event.target.value
                    )
                  }
                />
              </label>


              <label>
                Loss (%)

                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={lossPct}
                  onChange={(event) =>
                    setLossPct(
                      event.target.value
                    )
                  }
                />
              </label>


              <label>
                Bandwidth (Mbit)

                <input
                  type="number"
                  min="0"
                  max="100000"
                  value={rateMbit}
                  onChange={(event) =>
                    setRateMbit(
                      event.target.value
                    )
                  }
                />
              </label>
            </div>


            <div className="impairment-actions">
              <button
                type="button"
                className="capture-primary"
                onClick={applyImpairment}
                disabled={
                  impairmentBusy
                }
              >
                {
                  impairmentBusy
                    ? 'Applying...'
                    : 'Apply Impairment'
                }
              </button>

              <button
                type="button"
                className="capture-secondary"
                onClick={clearImpairment}
                disabled={
                  impairmentBusy
                }
              >
                Clear
              </button>
            </div>


            {impairmentRaw && (
              <code className="qdisc-preview">
                {impairmentRaw}
              </code>
            )}
          </section>


          <section className="link-tool-section">
            <h3>
              Packet Capture
            </h3>

            <div className="capture-link">
              <div>
                <span>Link</span>

                <strong>
                  {
                    link.portLabel ||
                    '-'
                  }
                </strong>
              </div>

              <div>
                <span>Status</span>

                <strong
                  className={
                    `capture-state ${status}`
                  }
                >
                  {status.toUpperCase()}
                </strong>
              </div>

              {runtimeInterface && (
                <div>
                  <span>
                    Runtime interface
                  </span>

                  <code>
                    {runtimeInterface}
                  </code>
                </div>
              )}

              {captureId && (
                <>
                  <div>
                    <span>
                      Capture ID
                    </span>

                    <code>
                      {captureId}
                    </code>
                  </div>

                  <div>
                    <span>
                      Captured
                    </span>

                    <strong>
                      {
                        formatBytes(
                          sizeBytes
                        )
                      }
                    </strong>
                  </div>
                </>
              )}
            </div>


            <div className="capture-inline-actions">
              {status === 'ready' && (
                <button
                  type="button"
                  className="capture-primary"
                  onClick={startCapture}
                >
                  Start Capture
                </button>
              )}

              {status === 'starting' && (
                <button
                  type="button"
                  className="capture-primary"
                  disabled
                >
                  Starting...
                </button>
              )}

              {status === 'running' && (
                <button
                  type="button"
                  className="capture-stop"
                  onClick={stopCapture}
                >
                  Stop Capture
                </button>
              )}

              {status === 'stopping' && (
                <button
                  type="button"
                  className="capture-stop"
                  disabled
                >
                  Stopping...
                </button>
              )}

              {finished && (
                <>
                  <button
                    type="button"
                    className="capture-secondary"
                    onClick={() =>
                      loadPreview(
                        captureId
                      )
                    }
                    disabled={
                      previewStatus ===
                      'loading'
                    }
                  >
                    {
                      previewStatus ===
                      'loading'
                        ? 'Loading Preview...'
                        : 'Refresh Preview'
                    }
                  </button>

                  <button
                    type="button"
                    className="capture-primary"
                    onClick={
                      downloadCapture
                    }
                  >
                    Download PCAP
                  </button>
                </>
              )}
            </div>


            {finished && (
              <div className="packet-preview">
                <div className="packet-preview-header">
                  <div>
                    <strong>
                      Packet Preview
                    </strong>

                    <span>
                      First {
                        previewLimit
                      } packets
                    </span>
                  </div>

                  {
                    previewStatus ===
                    'ready' && (
                      <div className="packet-preview-summary">
                        <strong>
                          {
                            previewReturned
                          }
                        </strong>

                        <span>
                          packets
                        </span>

                        {
                          previewTruncated &&
                          (
                            <span className="packet-preview-truncated">
                              more available
                            </span>
                          )
                        }
                      </div>
                    )
                  }
                </div>


                {
                  previewStatus ===
                  'idle' && (
                    <div className="packet-preview-empty">
                      Preview will be loaded
                      after the capture stops.
                    </div>
                  )
                }


                {
                  previewStatus ===
                  'loading' && (
                    <div className="packet-preview-empty">
                      Reading captured
                      packets...
                    </div>
                  )
                }


                {
                  previewStatus ===
                  'error' && (
                    <div className="packet-preview-error">
                      {
                        previewError ||
                        'Could not load preview.'
                      }
                    </div>
                  )
                }


                {
                  previewStatus ===
                  'ready' &&
                  previewPackets.length ===
                    0 && (
                    <div className="packet-preview-empty">
                      No packets were captured.
                    </div>
                  )
                }


                {
                  previewStatus ===
                  'ready' &&
                  previewPackets.length >
                    0 && (
                    <div className="packet-preview-table-wrap">
                      <table className="packet-preview-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Time</th>
                            <th>Source</th>
                            <th>Destination</th>
                            <th>Protocol</th>
                            <th>Length</th>
                            <th>Info</th>
                          </tr>
                        </thead>

                        <tbody>
                          {
                            previewPackets.map(
                              (packet) => (
                                <tr
                                  key={
                                    `${
                                      packet.number
                                    }-${
                                      packet.time
                                    }`
                                  }
                                >
                                  <td className="packet-number">
                                    {
                                      packet.number
                                    }
                                  </td>

                                  <td className="packet-time">
                                    {
                                      formatPacketTime(
                                        packet.time
                                      )
                                    }
                                  </td>

                                  <td>
                                    <code>
                                      {
                                        packet.source ||
                                        '-'
                                      }
                                    </code>
                                  </td>

                                  <td>
                                    <code>
                                      {
                                        packet.destination ||
                                        '-'
                                      }
                                    </code>
                                  </td>

                                  <td>
                                    <span className="packet-protocol">
                                      {
                                        packet.protocol ||
                                        '-'
                                      }
                                    </span>
                                  </td>

                                  <td className="packet-length">
                                    {
                                      packet.length ??
                                      '-'
                                    }
                                  </td>

                                  <td className="packet-info">
                                    {
                                      packet.info ||
                                      '-'
                                    }
                                  </td>
                                </tr>
                              )
                            )
                          }
                        </tbody>
                      </table>
                    </div>
                  )
                }
              </div>
            )}
          </section>


          {error && (
            <div className="capture-error">
              {error}
            </div>
          )}
        </div>


        <div className="capture-footer">
          <button
            type="button"
            className="capture-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}


export default LinkCaptureModal
