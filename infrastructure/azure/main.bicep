param location string = resourceGroup().location
param environment string = 'production'

resource vnet 'Microsoft.Network/virtualNetworks@2021-02-01' = {
  name: 'sintraprime-vnet'
  location: location
  properties: {
    addressSpace: { addressPrefixes: [ '10.0.0.0/16' ] }
    subnets: [
      { name: 'AppSubnet', properties: { addressPrefix: '10.0.1.0/24' } }
    ]
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2021-02-01' = {
  name: 'sintraprime-plan'
  location: location
  sku: { name: 'P1V2', tier: 'Premium', capacity: 3 }
  properties: { reserved: true }
}

resource sqlServer 'Microsoft.Sql/servers@2019-06-01' = {
  name: 'sintraprime-sql'
  location: location
  properties: { administratorLogin: 'sqladmin', version: '12.0' }
}

output vnetId string = vnet.id
output appPlanId string = appServicePlan.id
output sqlServerId string = sqlServer.id
