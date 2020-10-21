from micra_store.structure import List, json_object_type

longcat_api_requests = List(
  identifier='longcat_api_requests',
  title='Longcat API Requests',
  description='Job requests submitted by Longcat API.',
  key='longcat_api_requests',
  content_type=json_object_type.identifier,
  tags={'job'}
)