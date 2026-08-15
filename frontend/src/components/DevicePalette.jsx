import {
  useMemo,
  useState,
} from 'react'

import './DevicePalette.css'


function isDeviceDisabled(device) {
  return (
    device?.enabled === false ||
    device?.availability ===
      'coming-soon'
  )
}


function getDeviceIcon(device) {
  if (
    device.id === 'cloud-nat'
  ) {
    return '☁'
  }

  if (
    device.id === 'network'
  ) {
    return '◇'
  }

  if (
    device.category === 'endpoint'
  ) {
    return '▣'
  }

  if (
    device.vendor === 'fortinet'
  ) {
    return '▤'
  }

  return '▦'
}


function DeviceSection({
  title,
  devices,
}) {
  if (!devices.length) {
    return null
  }


  function onDragStart(
    event,
    device,
  ) {
    if (
      isDeviceDisabled(
        device
      )
    ) {
      event.preventDefault()
      return
    }

    event.dataTransfer.effectAllowed =
      'copy'

    event.dataTransfer.setData(
      'application/unidac-device',
      JSON.stringify({
        template_id:
          device.id,
      })
    )
  }


  return (
    <section className="device-section">
      <div className="device-section-title">
        {title}
      </div>


      <div className="device-section-list">
        {devices.map((device) => {
          const disabled =
            isDeviceDisabled(
              device
            )

          return (
            <div
              key={device.id}
              className={[
                'device-item',
                disabled
                  ? 'device-item-disabled'
                  : '',
              ]
                .filter(Boolean)
                .join(' ')}
              draggable={!disabled}
              aria-disabled={
                disabled
              }
              title={
                disabled
                  ? `${device.name} - Coming Soon`
                  : device.description
              }
              onDragStart={(
                event
              ) =>
                onDragStart(
                  event,
                  device,
                )
              }
            >
              <div className="device-icon">
                {getDeviceIcon(
                  device
                )}
              </div>


              <div className="device-info">
                <div className="device-title-row">
                  <strong>
                    {device.name}
                  </strong>

                  {disabled && (
                    <span className="device-badge">
                      COMING SOON
                    </span>
                  )}
                </div>

                <span>
                  {
                    disabled
                      ? 'Runtime not available yet'
                      : device.description
                  }
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}


function formatVendor(
  vendor,
) {
  if (!vendor) {
    return 'Appliances'
  }

  return (
    vendor.charAt(0).toUpperCase()
    + vendor.slice(1)
  )
}


function DevicePalette({
  devices = [],
  onImportImage,
}) {
  const [
    search,
    setSearch,
  ] = useState('')


  const filteredDevices =
    useMemo(
      () => {
        const query =
          search
            .trim()
            .toLowerCase()

        if (!query) {
          return devices
        }

        return devices.filter(
          (device) => {
            const text = [
              device.name,
              device.vendor,
              device.category,
              device.description,
              device.id,
            ]
              .filter(Boolean)
              .join(' ')
              .toLowerCase()

            return text.includes(
              query
            )
          }
        )
      },
      [
        devices,
        search,
      ],
    )


  const infrastructure =
    filteredDevices.filter(
      (device) =>
        device.category ===
        'infrastructure'
    )


  const endpoints =
    filteredDevices.filter(
      (device) =>
        device.category ===
        'endpoint'
    )


  const appliances =
    filteredDevices.filter(
      (device) =>
        device.category !==
          'infrastructure'
        &&
        device.category !==
          'endpoint'
    )


  const vendors =
    [
      ...new Set(
        appliances
          .map(
            (device) =>
              device.vendor
          )
          .filter(Boolean)
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
            Drag to canvas
          </span>
        </div>


        <button
          type="button"
          className="palette-import-image"
          onClick={
            onImportImage
          }
        >
          Import Image
        </button>
      </div>


      <div className="palette-search">
        <input
          type="text"
          placeholder="Search devices..."
          value={search}
          onChange={(event) =>
            setSearch(
              event.target.value
            )
          }
        />
      </div>


      <div className="palette-content">
        <DeviceSection
          title="Infrastructure"
          devices={
            infrastructure
          }
        />

        <DeviceSection
          title="Endpoints"
          devices={
            endpoints
          }
        />


        {vendors.map(
          (vendor) => (
            <DeviceSection
              key={vendor}
              title={
                formatVendor(
                  vendor
                )
              }
              devices={
                appliances.filter(
                  (device) =>
                    device.vendor
                    === vendor
                )
              }
            />
          )
        )}


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
