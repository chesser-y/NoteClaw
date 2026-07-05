<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as d3 from 'd3'
import type { KGEdge, KGNode } from '../../api/types'

const props = defineProps<{
  nodes: KGNode[]
  edges: KGEdge[]
  searchQuery?: string
}>()

const emit = defineEmits<{
  'select-node': [node: KGNode | null]
  'focus-tag': [tag: string]
}>()

const host = ref<HTMLElement | null>(null)
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let simulation: any = null
let linkSel: d3.Selection<SVGLineElement, GraphEdge, SVGGElement, unknown> | null = null
let nodeSel: d3.Selection<SVGGElement, GraphNode, SVGGElement, unknown> | null = null
let currentNodes: GraphNode[] = []
let currentEdges: GraphEdge[] = []
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null
let bridgeIds: Set<string> = new Set()

type GraphNode = d3.SimulationNodeDatum & {
  id: string
  label: string
  type: KGNode['type']
  weight: number
  radius: number
  color: string
}

type GraphEdge = {
  source: string | GraphNode
  target: string | GraphNode
  type: KGEdge['type']
  weight: number
}

const TYPE_COLOR: Record<string, string> = {
  tag: '#626be6',
  note: '#7d808a',
  category: '#4aaeff',
  content_type: '#e0a23a',
}

function computeRadius(n: KGNode) {
  if (n.type === 'tag') {
    const w = n.weight ?? 1
    return 8 + Math.min(20, Math.sqrt(w) * 4)
  }
  if (n.type === 'category') return 14
  if (n.type === 'content_type') return 12
  return 4
}

/**
 * Local "bridge" heuristic: a tag node is a bridge when its tag_cooccurs neighbours
 * are poorly interconnected — i.e. it's the only path between otherwise separate clusters.
 * Score = sum over neighbour pairs (a, b) of (1 if a-b edge missing else 0).
 */
function computeBridges(nodes: GraphNode[], edges: GraphEdge[]): Set<string> {
  const adj = new Map<string, Set<string>>()
  for (const n of nodes) adj.set(n.id, new Set())
  for (const e of edges) {
    if (e.type !== 'tag_cooccurs') continue
    const s = typeof e.source === 'string' ? e.source : e.source.id
    const t = typeof e.target === 'string' ? e.target : e.target.id
    adj.get(s)?.add(t)
    adj.get(t)?.add(s)
  }
  const out = new Set<string>()
  for (const n of nodes) {
    if (n.type !== 'tag') continue
    const neighbors = [...(adj.get(n.id) ?? [])]
    if (neighbors.length < 2) continue
    let missing = 0
    let pairs = 0
    for (let i = 0; i < neighbors.length; i++) {
      for (let j = i + 1; j < neighbors.length; j++) {
        pairs += 1
        if (!adj.get(neighbors[i])?.has(neighbors[j])) missing += 1
      }
    }
    if (pairs === 0) continue
    // neighbours poorly interconnected → bridge
    if (missing / pairs >= 0.7 && neighbors.length >= 3) {
      out.add(n.id)
    }
  }
  return out
}

function buildGraph() {
  if (!host.value) return
  const rect = host.value.getBoundingClientRect()
  const width = Math.max(800, rect.width || 1200)
  const height = Math.max(500, rect.height || 700)

  d3.select(host.value).selectAll('*').remove()

  svg = d3.select(host.value)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet') as d3.Selection<SVGSVGElement, unknown, null, undefined>

  const root = svg.append('g').attr('class', 'root')

  zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      root.attr('transform', event.transform.toString())
    })
  svg.call(zoomBehavior)

  currentNodes = props.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    type: n.type,
    weight: n.weight ?? 1,
    radius: computeRadius(n),
    color: TYPE_COLOR[n.type] ?? '#999',
  }))

  currentEdges = props.edges.map((e) => ({
    source: e.source,
    target: e.target,
    type: e.type,
    weight: e.weight ?? 1,
  }))

  bridgeIds = computeBridges(currentNodes, currentEdges)

  const idToNode = new Map(currentNodes.map((n) => [n.id, n]))

  linkSel = root.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(currentEdges)
    .enter()
    .append('line')
    .attr('stroke', (d) => edgeColor(d.type))
    .attr('stroke-width', (d) => Math.max(0.6, Math.min(4, Math.sqrt(d.weight) * 0.9)))
    .attr('stroke-opacity', 0.45)
    .attr('stroke-dasharray', (d) => (d.type === 'has_tag' ? '2,3' : null))

  // Bridge halo ring (rendered before nodes so the ring sits behind)
  root.append('g')
    .attr('class', 'bridges')
    .selectAll('circle')
    .data(currentNodes.filter((n) => bridgeIds.has(n.id)))
    .enter()
    .append('circle')
    .attr('class', 'bridge-halo')
    .attr('r', (d) => d.radius + 8)
    .attr('fill', 'none')
    .attr('stroke', '#f0b8ad')
    .attr('stroke-width', 1.2)
    .attr('stroke-dasharray', '3,3')
    .attr('opacity', 0.7)

  nodeSel = root.append('g')
    .attr('class', 'nodes')
    .selectAll('g.node')
    .data(currentNodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .style('cursor', 'pointer')
    .call(d3.drag<any, GraphNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation?.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation?.alphaTarget(0)
        d.fx = null
        d.fy = null
      }))

  nodeSel.append('circle')
    .attr('r', (d) => d.radius)
    .attr('fill', (d) => d.color)
    .attr('stroke', '#0d1011')
    .attr('stroke-width', 1.5)

  nodeSel.append('text')
    .attr('class', 'node-label')
    .text((d) => d.type === 'note' ? '' : d.label)
    .attr('x', (d) => d.radius + 4)
    .attr('y', 4)
    .attr('font-size', (d) => d.type === 'tag' ? 11 : 10)
    .attr('fill', '#e6e7ea')
    .attr('font-weight', (d) => d.type === 'tag' ? 600 : 400)
    .attr('pointer-events', 'none')

  nodeSel
    .on('mouseover', (_event, d) => highlight(d))
    .on('mouseout', () => unhighlight())
    .on('click', (_event, d) => {
      emit('select-node', toKgNode(d))
      if (d.type === 'tag') emit('focus-tag', d.label)
    })

  simulation = d3.forceSimulation<GraphNode>(currentNodes)
    .force('link', d3.forceLink<GraphNode, GraphEdge>(currentEdges)
      .id((d) => (d as GraphNode).id)
      .distance((d) => d.type === 'has_tag' ? 60 : 90)
      .strength((d) => d.type === 'tag_cooccurs' ? 0.5 : 0.15))
    .force('charge', d3.forceManyBody().strength((d: any) => (d as GraphNode).type === 'tag' ? -180 : -40))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide<GraphNode>().radius((d) => d.radius + 6))
    .alpha(1)
    .alphaDecay(0.025)
    .on('tick', () => {
      if (!linkSel || !nodeSel) return
      linkSel
        .attr('x1', (d) => (idToNode.get(d.source as string)?.x) ?? 0)
        .attr('y1', (d) => (idToNode.get(d.source as string)?.y) ?? 0)
        .attr('x2', (d) => (idToNode.get(d.target as string)?.x) ?? 0)
        .attr('y2', (d) => (idToNode.get(d.target as string)?.y) ?? 0)
      // Keep halo rings following their nodes
      root.selectAll<SVGCircleElement, GraphNode>('.bridge-halo').attr('transform', (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`)
      nodeSel.attr('transform', (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`)
    })

  applySearchFilter(props.searchQuery)
}

function edgeColor(type: KGEdge['type']) {
  switch (type) {
    case 'tag_cooccurs': return '#626be6'
    case 'has_tag': return '#5a5d68'
    case 'category_tag': return '#4aaeff'
    case 'content_type_tag': return '#e0a23a'
    default: return '#444'
  }
}

function neighborsWithin(edges: GraphEdge[], start: GraphNode, maxDepth: number) {
  const adj = new Map<string, Set<string>>()
  for (const e of edges) {
    const s = typeof e.source === 'string' ? e.source : (e.source as GraphNode).id
    const t = typeof e.target === 'string' ? e.target : (e.target as GraphNode).id
    if (!adj.has(s)) adj.set(s, new Set())
    if (!adj.has(t)) adj.set(t, new Set())
    adj.get(s)!.add(t)
    adj.get(t)!.add(s)
  }
  const visited = new Set<string>([start.id])
  const frontier = [start.id]
  for (let depth = 0; depth < maxDepth; depth++) {
    const next: string[] = []
    for (const id of frontier) {
      for (const n of adj.get(id) ?? []) {
        if (!visited.has(n)) {
          visited.add(n)
          next.push(n)
        }
      }
    }
    frontier.length = 0
    frontier.push(...next)
  }
  return visited
}

function highlight(d: GraphNode) {
  if (!nodeSel || !linkSel) return
  const neighborIds = neighborsWithin(currentEdges, d, 2)
  nodeSel.attr('opacity', (n) => (neighborIds.has(n.id) ? 1 : 0.12))
  nodeSel.select('circle').attr('stroke', (n) => (n.id === d.id ? '#fff' : '#0d1011'))
  linkSel
    .attr('stroke-opacity', (e) => {
      const s = typeof e.source === 'string' ? e.source : (e.source as GraphNode).id
      const t = typeof e.target === 'string' ? e.target : (e.target as GraphNode).id
      return neighborIds.has(s) && neighborIds.has(t) ? 0.85 : 0.04
    })
    .attr('stroke-width', (e) => {
      const s = typeof e.source === 'string' ? e.source : (e.source as GraphNode).id
      const t = typeof e.target === 'string' ? e.target : (e.target as GraphNode).id
      return neighborIds.has(s) && neighborIds.has(t) ? Math.max(1.4, Math.sqrt(e.weight)) : 0.6
    })
}

function unhighlight() {
  if (!nodeSel || !linkSel) return
  applySearchFilter(props.searchQuery)
  nodeSel.select('circle').attr('stroke', '#0d1011')
  linkSel
    .attr('stroke-opacity', 0.45)
    .attr('stroke-width', (d) => Math.max(0.6, Math.min(4, Math.sqrt(d.weight) * 0.9)))
}

function applySearchFilter(raw: string | undefined) {
  if (!nodeSel) return
  const q = (raw ?? '').trim().toLowerCase()
  if (!q) {
    nodeSel.attr('opacity', 1)
    return
  }
  nodeSel.attr('opacity', (n) => (n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q) ? 1 : 0.18))
}

function toKgNode(d: GraphNode): KGNode {
  return {
    id: d.id,
    label: d.label,
    type: d.type,
    weight: d.weight,
  }
}

function onResize() {
  if (!host.value || !svg) return
  const rect = host.value.getBoundingClientRect()
  svg.attr('viewBox', `0 0 ${Math.max(800, rect.width)} ${Math.max(500, rect.height)}`)
  simulation?.force('center', d3.forceCenter(rect.width / 2, rect.height / 2))
  simulation?.alpha(0.3).restart()
}

let resizeObserver: ResizeObserver | null = null

watch(
  () => [props.nodes, props.edges],
  () => {
    buildGraph()
  },
  { deep: false },
)

watch(
  () => props.searchQuery,
  (q) => applySearchFilter(q),
)

onMounted(() => {
  buildGraph()
  if (host.value) {
    resizeObserver = new ResizeObserver(() => onResize())
    resizeObserver.observe(host.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  simulation?.stop()
  if (svg) svg.selectAll('*').remove()
})

defineExpose({
  highlightNodeById(id: string) {
    const target = currentNodes.find((n) => n.id === id)
    if (target) highlight(target)
  },
  resetHighlight() {
    unhighlight()
  },
})
</script>

<template>
  <div ref="host" class="graph-canvas" />
</template>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 100%;
  background:
    radial-gradient(circle at 30% 20%, rgba(98, 107, 230, 0.08), transparent 50%),
    radial-gradient(circle at 70% 80%, rgba(74, 174, 255, 0.06), transparent 55%),
    var(--bg, #080a0d);
  overflow: hidden;
}
.graph-canvas :deep(svg) {
  display: block;
  cursor: grab;
}
.graph-canvas :deep(svg:active) {
  cursor: grabbing;
}
.graph-canvas :deep(.node) {
  transition: opacity 180ms ease;
}
.graph-canvas :deep(.links line) {
  transition: stroke-opacity 180ms ease, stroke-width 180ms ease;
}
.graph-canvas :deep(.bridge-halo) {
  transition: opacity 200ms ease;
  animation: halo-pulse 2.4s ease-in-out infinite;
}
@keyframes halo-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 0.9; }
}
</style>
