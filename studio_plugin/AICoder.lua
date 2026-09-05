-- AICoder: side panel that talks to the local luau-coder Ollama model.
-- Install: copy this file into %LOCALAPPDATA%\Roblox\Plugins\
-- Requires: Studio Settings > Security > Allow HTTP Requests, and
--           `ollama create luau-coder -f Modelfile` already run + `ollama serve` running.

local toolbar = plugin:CreateToolbar("AI Coder")
local button = toolbar:CreateButton("Ask AI", "Ask the local Luau model", "")

local widget = plugin:CreateDockWidgetPluginGui(
	"AICoderWidget",
	DockWidgetPluginGuiInfo.new(Enum.InitialDockState.Right, false, false, 320, 400, 250, 300)
)
widget.Title = "AI Coder"

local frame = Instance.new("Frame")
frame.Size = UDim2.fromScale(1, 1)
frame.BackgroundColor3 = Color3.fromRGB(30, 30, 30)
frame.Parent = widget

local promptBox = Instance.new("TextBox")
promptBox.PlaceholderText = "Describe the Luau code you want..."
promptBox.Size = UDim2.new(1, -20, 0, 80)
promptBox.Position = UDim2.new(0, 10, 0, 10)
promptBox.ClearTextOnFocus = false
promptBox.TextWrapped = true
promptBox.MultiLine = true
promptBox.Parent = frame

local askButton = Instance.new("TextButton")
askButton.Text = "Ask"
askButton.Size = UDim2.new(1, -20, 0, 30)
askButton.Position = UDim2.new(0, 10, 0, 100)
askButton.Parent = frame

local responseBox = Instance.new("TextBox")
responseBox.PlaceholderText = "Response will appear here..."
responseBox.Size = UDim2.new(1, -20, 1, -180)
responseBox.Position = UDim2.new(0, 10, 0, 140)
responseBox.ClearTextOnFocus = false
responseBox.TextWrapped = true
responseBox.MultiLine = true
responseBox.TextXAlignment = Enum.TextXAlignment.Left
responseBox.TextYAlignment = Enum.TextYAlignment.Top
responseBox.Parent = frame

local insertButton = Instance.new("TextButton")
insertButton.Text = "Insert into script"
insertButton.Size = UDim2.new(1, -20, 0, 30)
insertButton.Position = UDim2.new(0, 10, 1, -30)
insertButton.AnchorPoint = Vector2.new(0, 1)
insertButton.Parent = frame

local HttpService = game:GetService("HttpService")
local ScriptEditorService = game:GetService("ScriptEditorService")

local lastResponse = ""

local function extractCode(text)
	local code = text:match("```luau%s*(.-)```") or text:match("```lua%s*(.-)```")
	return code or text
end

askButton.MouseButton1Click:Connect(function()
	responseBox.Text = "Thinking..."
	local ok, result = pcall(function()
		local body = HttpService:JSONEncode({
			model = "luau-coder",
			prompt = promptBox.Text,
			stream = false,
		})
		local res = HttpService:RequestAsync({
			Url = "http://localhost:11434/api/generate",
			Method = "POST",
			Headers = { ["Content-Type"] = "application/json" },
			Body = body,
		})
		return HttpService:JSONDecode(res.Body)
	end)

	if ok and result.response then
		lastResponse = extractCode(result.response)
		responseBox.Text = lastResponse
	else
		responseBox.Text = "Error: " .. tostring(result)
	end
end)

insertButton.MouseButton1Click:Connect(function()
	local scriptDoc = ScriptEditorService:FindScriptDocument(nil)
	local currentScript = ScriptEditorService:GetActiveScript()
	if not currentScript then
		warn("AICoder: no active script open")
		return
	end
	local doc = ScriptEditorService:FindScriptDocument(currentScript)
	if not doc then
		warn("AICoder: could not open script document")
		return
	end
	local lineCount = doc:GetLineCount()
	doc:EditTextAsync(lastResponse, lineCount, doc:GetLine(lineCount):len() + 1, lineCount, doc:GetLine(lineCount):len() + 1)
end)

button.Click:Connect(function()
	widget.Enabled = not widget.Enabled
end)
