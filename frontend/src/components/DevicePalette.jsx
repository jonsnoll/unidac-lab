import { useMemo, useState } from 'react'

import './DevicePalette.css'


function DeviceItem({ device }) {
  const onDragStart = (event) => {
    const payload = {
      template_id: device.id,
    }

    event.dataTransfer.setData(
      'application/unidac-device',
      JSON.stringify(payload),
    )

    event.dataTransfer.setData(
      'text/plain',
      device.id,
    )

    event.dataTransfer.effectAllowed = 'copy'
  }


  return (
    <div
      className="device-item"
      title={device.description}
      draggable
      onDragStart={onDragStart}
    >
      <div
        className={
          `device-icon device-icon-${device.kind}`
        }
      >
        {device.kind === 'cloud' && '☁'}
        {device.kind === 'network' && '◇'}
        {device.kind === 'vm' && '▣'}
        {device.kind === 'network-appliance' && '▤'}
      </div>

      <div className="device-info">
        <strong>
          {device.name}
        </strong>

        <span>
          {device.runtime}

          {device.image_required
            ? ' · image required'
            : ''}
        </span>
      </div>
    </div>
  )
}


function DeviceSection({
  title,
  devices,
}) {
  if (!devices.length) {
    return null
  }


  return (
    <section className="device-section">
      <div className="device-section-title">
        {title}
      </div>

      <div className="device-section-list">
        {devices.map((device) => (
          <DeviceItem
            key={device.id}
            device={device}
          />
        ))}
      </div>
    </section>
  )
}


function DevicePalette({ devices }) {
  const [search, setSearch] = useState('')


  const filteredDevices = useMemo(() => {
    const query =
      search.trim().toLowerCase()

    if (!query) {
      return devices
    }


    return devices.filter((device) => {
      const text = [
        device.name,
        device.vendor,
        device.category,
        device.kind,
        device.description,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return text.includes(query)
    })
  }, [devices, search])


  const infrastructure =
    filteredDevices.filter(
      (device) =>
        device.category ===
        'infrastructure'
    )


  const endpoints =
    filteredDevices.filter(
      (device) =>
        device.category === 'endpoint'
    )


  const appliances =
    filteredDevices.filter(
      (device) =>
        device.category !==
          'infrastructure' &&
        device.category !==
          'endpoint'
    )


  const vendors = [
    ...new Set(
      appliances.map(
        (device) => device.vendor
      )
    ),
  ].sort()


  return (
    <aside className="device-palette">
      <div className="palette-header">
        <div>
          <strong>
            Devices
          </strong>

          <span>
            {devices.length} available
          </span>
        </div>
      </div>


      <div className="palette-search">
        <input
          type="text"
          placeholder="Search devices..."
          value={search}
          onChange={(event) =>
            setSearch(event.target.value)
          }
        />
      </div>


      <div className="palette-content">
        <DeviceSection
          title="Infrastructure"
          devices={infrastructure}
        />

        <DeviceSection
          title="Endpoints"
          devices={endpoints}
        />


        {vendors.map((vendor) => (
          <DeviceSection
            key={vendor}
            title={vendor}
            devices={
              appliances.filter(
                (device) =>
                  device.vendor === vendor
              )
            }
          />
        ))}


        {!filteredDevices.length && (
          <div className="palette-empty">
            No devices found.
          </div>
        )}
      </div>
    </aside>
  )
}


export default DevicePalette
