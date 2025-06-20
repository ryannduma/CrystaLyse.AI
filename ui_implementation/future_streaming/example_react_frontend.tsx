// Example React Frontend for CrystaLyse.AI WebSocket Interface
// This demonstrates real-time agent transparency

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';

// Types
interface AgentEvent {
  id: string;
  timestamp: number;
  type: string;
  agent_name: string;
  mode: string;
  data: Record<string, any>;
  metadata?: Record<string, any>;
}

interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'error';
  args?: Record<string, any>;
  result?: Record<string, any>;
  startTime: number;
  endTime?: number;
}

// Custom hook for WebSocket connection
const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  
  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onopen = () => {
      setConnectionState('connected');
      setSocket(ws);
      console.log('🔗 Connected to CrystaLyse.AI');
    };
    
    ws.onmessage = (event) => {
      const agentEvent: AgentEvent = JSON.parse(event.data);
      setEvents(prev => [...prev, agentEvent]);
      console.log('📥 Received event:', agentEvent.type);
    };
    
    ws.onclose = () => {
      setConnectionState('disconnected');
      setSocket(null);
      console.log('🔌 Disconnected from CrystaLyse.AI');
    };
    
    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };
    
    return () => {
      ws.close();
    };
  }, [url]);
  
  const sendMessage = (message: Record<string, any>) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
      console.log('📤 Sent message:', message.type);
    }
  };
  
  return { events, sendMessage, connectionState };
};

// Agent Reasoning Panel Component
const AgentReasoningPanel: React.FC<{ events: AgentEvent[] }> = ({ events }) => {
  const reasoningEvents = events.filter(e => 
    ['reasoning_start', 'reasoning_update', 'reasoning_end'].includes(e.type)
  );
  
  const currentReasoning = reasoningEvents[reasoningEvents.length - 1];
  
  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">🧠 Agent Reasoning</h3>
        {currentReasoning && (
          <Badge variant={currentReasoning.type === 'reasoning_end' ? 'default' : 'secondary'}>
            {currentReasoning.mode === 'rigorous' ? '🔬 Rigorous Mode' : '⚡ Creative Mode'}
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64">
          {reasoningEvents.map((event, index) => (
            <div key={event.id} className="mb-3 p-3 bg-gray-50 rounded">
              <div className="text-xs text-gray-500 mb-1">
                {new Date(event.timestamp * 1000).toLocaleTimeString()}
              </div>
              <div className="font-medium text-sm">
                {event.type === 'reasoning_start' && '🎯 Starting Analysis'}
                {event.type === 'reasoning_update' && '💭 Thinking...'}
                {event.type === 'reasoning_end' && '✅ Analysis Complete'}
              </div>
              <div className="text-sm mt-1">
                {event.data.reasoning || event.data.summary}
              </div>
              {event.data.formulas && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {event.data.formulas.map((formula: string, i: number) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {formula}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

// Tool Usage Panel Component
const ToolUsagePanel: React.FC<{ events: AgentEvent[] }> = ({ events }) => {
  const [activeTools, setActiveTools] = useState<Map<string, ToolCall>>(new Map());
  
  useEffect(() => {
    events.forEach(event => {
      if (event.type === 'tool_call_start') {
        const toolId = `${event.data.tool}-${event.timestamp}`;
        setActiveTools(prev => new Map(prev).set(toolId, {
          id: toolId,
          name: event.data.tool,
          status: 'running',
          args: event.data,
          startTime: event.timestamp
        }));
      } else if (event.type === 'tool_call_result') {
        // Find and update the corresponding tool call
        setActiveTools(prev => {
          const newMap = new Map(prev);
          for (const [key, tool] of newMap) {
            if (tool.name === event.data.tool && tool.status === 'running') {
              newMap.set(key, {
                ...tool,
                status: 'completed',
                result: event.data,
                endTime: event.timestamp
              });
              break;
            }
          }
          return newMap;
        });
      }
    });
  }, [events]);
  
  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">🔧 Tool Usage</h3>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64">
          {Array.from(activeTools.values()).map(tool => (
            <div key={tool.id} className="mb-3 p-3 border rounded">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Badge variant={tool.status === 'completed' ? 'default' : 'secondary'}>
                    {tool.name}
                  </Badge>
                  {tool.status === 'running' && (
                    <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  {tool.endTime ? 
                    `${((tool.endTime - tool.startTime)).toFixed(1)}s` :
                    `${((Date.now() / 1000 - tool.startTime)).toFixed(1)}s`
                  }
                </div>
              </div>
              
              {tool.args?.action && (
                <div className="text-sm text-gray-600 mb-1">
                  Action: {tool.args.action}
                </div>
              )}
              
              {tool.args?.formula && (
                <div className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                  {tool.args.formula}
                </div>
              )}
              
              {tool.result && (
                <div className="mt-2 text-xs">
                  {tool.name === 'SMACT' && (
                    <div className="space-y-1">
                      <div>✅ Charge balanced: {tool.result.result?.charge_balanced ? 'Yes' : 'No'}</div>
                      <div>⚡ Valid oxidation states: {tool.result.result?.oxidation_states}</div>
                    </div>
                  )}
                  {tool.name === 'MACE' && (
                    <div className="space-y-1">
                      <div>🔋 Formation Energy: {tool.result.formation_energy?.toFixed(3)} eV/atom</div>
                      <div>📊 Hull Distance: {tool.result.hull_distance?.toFixed(3)} eV/atom</div>
                      <div>📏 Uncertainty: ±{tool.result.uncertainty?.toFixed(3)} eV</div>
                    </div>
                  )}
                  {tool.name === 'Chemeleon' && (
                    <div className="space-y-1">
                      <div>🏗️ Space Group: {tool.result.structure?.space_group}</div>
                      <div>📦 Volume: {tool.result.structure?.volume?.toFixed(1)} Ų</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

// Results Summary Panel
const ResultsPanel: React.FC<{ events: AgentEvent[] }> = ({ events }) => {
  const completionEvent = events.find(e => e.type === 'discovery_complete');
  const structureEvents = events.filter(e => e.type === 'structure_generated');
  const energyEvents = events.filter(e => e.type === 'energy_calculated');
  
  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">📊 Results Summary</h3>
      </CardHeader>
      <CardContent>
        {completionEvent ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-blue-50 rounded">
                <div className="text-2xl font-bold text-blue-600">
                  {completionEvent.data.total_materials}
                </div>
                <div className="text-sm text-gray-600">Materials Analysed</div>
              </div>
              <div className="text-center p-3 bg-green-50 rounded">
                <div className="text-2xl font-bold text-green-600">
                  {completionEvent.data.valid_materials}
                </div>
                <div className="text-sm text-gray-600">Validated Structures</div>
              </div>
            </div>
            
            <div className="text-sm">
              <strong>Elapsed Time:</strong> {completionEvent.data.elapsed_time}s
            </div>
            
            {structureEvents.length > 0 && (
              <div className="mt-4">
                <h4 className="font-semibold mb-2">Generated Structures:</h4>
                <div className="space-y-2">
                  {structureEvents.map((event, i) => (
                    <div key={i} className="p-2 bg-gray-50 rounded text-sm">
                      <div className="font-mono">{event.data.formula}</div>
                      <div className="text-xs text-gray-600">
                        Space Group: {event.data.structure?.space_group}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-gray-500 text-center py-8">
            No results yet. Submit a query to begin discovery.
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Memory Panel Component
const MemoryPanel: React.FC<{ events: AgentEvent[]; onSearch: (query: string) => void }> = ({ events, onSearch }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const memoryEvents = events.filter(e => e.type === 'memory_read');
  
  const handleSearch = () => {
    if (searchQuery.trim()) {
      onSearch(searchQuery);
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">🧠 Memory</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="Search memory..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch} size="sm">Search</Button>
          </div>
          
          <ScrollArea className="h-48">
            {memoryEvents.map((event, i) => (
              <div key={i} className="mb-2 p-2 bg-purple-50 rounded text-sm">
                <div className="font-medium">Query: {event.data.query}</div>
                <div className="text-xs text-gray-600">
                  Found {event.data.count} memories
                </div>
              </div>
            ))}
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
};

// Main Discovery Interface Component
const CrystaLyseInterface: React.FC = () => {
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'creative' | 'rigorous'>('creative');
  
  const { events, sendMessage, connectionState } = useWebSocket(
    `ws://localhost:8000/ws/discovery/${sessionId}`
  );
  
  const handleSubmitQuery = () => {
    if (query.trim()) {
      sendMessage({
        type: 'discovery_request',
        query: query,
        mode: mode
      });
      setQuery('');
    }
  };
  
  const handleMemorySearch = (searchQuery: string) => {
    sendMessage({
      type: 'memory_search',
      query: searchQuery
    });
  };
  
  const connectionBadge = {
    connected: { variant: 'default' as const, text: '🟢 Connected' },
    connecting: { variant: 'secondary' as const, text: '🟡 Connecting' },
    disconnected: { variant: 'destructive' as const, text: '🔴 Disconnected' }
  }[connectionState];
  
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold">CrystaLyse.AI Discovery Interface</h1>
            <Badge variant={connectionBadge.variant}>
              {connectionBadge.text}
            </Badge>
          </div>
          <p className="text-gray-600 mt-2">
            Real-time computational materials discovery with full transparency
          </p>
        </div>
        
        {/* Query Input */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Describe the materials you want to discover..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSubmitQuery()}
                  className="flex-1"
                />
                <select 
                  value={mode} 
                  onChange={(e) => setMode(e.target.value as 'creative' | 'rigorous')}
                  className="px-3 py-2 border rounded"
                >
                  <option value="creative">⚡ Creative Mode</option>
                  <option value="rigorous">🔬 Rigorous Mode</option>
                </select>
                <Button 
                  onClick={handleSubmitQuery}
                  disabled={!query.trim() || connectionState !== 'connected'}
                >
                  Discover
                </Button>
              </div>
              
              {/* Quick Examples */}
              <div className="flex gap-2 flex-wrap">
                <span className="text-sm text-gray-500">Examples:</span>
                {[
                  'Find novel battery cathode materials',
                  'Self-healing concrete additives',
                  'High-temperature supercapacitor electrodes'
                ].map((example, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    onClick={() => setQuery(example)}
                  >
                    {example}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Main Interface */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Agent Activity */}
          <div className="lg:col-span-2 space-y-6">
            <AgentReasoningPanel events={events} />
            <ToolUsagePanel events={events} />
          </div>
          
          {/* Right Column - Results and Memory */}
          <div className="space-y-6">
            <ResultsPanel events={events} />
            <MemoryPanel events={events} onSearch={handleMemorySearch} />
          </div>
        </div>
        
        {/* Event Log for Development */}
        {process.env.NODE_ENV === 'development' && (
          <Card className="mt-6">
            <CardHeader>
              <h3 className="text-lg font-semibold">🔍 Event Log (Dev)</h3>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-32">
                <pre className="text-xs">
                  {events.slice(-10).map(e => 
                    `${new Date(e.timestamp * 1000).toLocaleTimeString()} - ${e.type}: ${JSON.stringify(e.data, null, 2)}`
                  ).join('\n')}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default CrystaLyseInterface;