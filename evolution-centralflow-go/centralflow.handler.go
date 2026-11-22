package send_handler

import (
	"encoding/json"
	instance_model "github.com/evolution-foundation/evolution-go/pkg/instance/model"
	"github.com/gin-gonic/gin"
	"io"
	"net/http"
	"strings"
)

func (s *sendHandler) CentralFlow(ctx *gin.Context) {
	instance, ok := ctx.MustGet("instance").(*instance_model.Instance)
	if !ok {
		ctx.JSON(401, gin.H{"error": "invalid instance"})
		return
	}
	action := strings.TrimPrefix(ctx.Param("action"), "/")
	if ctx.Request.URL.Path == "/centralflow/capabilities" {
		action = "capabilities"
	}
	body := json.RawMessage(`{}`)
	if ctx.Request.Method != "GET" {
		ctx.Request.Body = http.MaxBytesReader(ctx.Writer, ctx.Request.Body, 24*1024*1024)
		data, err := io.ReadAll(ctx.Request.Body)
		if err != nil {
			ctx.JSON(413, gin.H{"error": "request too large"})
			return
		}
		body = data
	}
	result, err := s.sendMessageService.CentralFlow(action, body, instance)
	if err != nil {
		ctx.JSON(409, gin.H{"error": "CentralFlow GO operation failed; verify instance, permissions and requested operation"})
		return
	}
	ctx.JSON(200, gin.H{"message": "success", "data": result})
}
