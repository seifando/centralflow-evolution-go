"""Apply only to the exact official source snapshot; never to a running container."""
from pathlib import Path
import hashlib,json,shutil,sys
root=Path(sys.argv[1]).resolve();bundle=Path(__file__).resolve().parent
manifest=json.loads((bundle/'upstream.json').read_text())
targets={
 'pkg/sendMessage/service/send_service.go':('type SendService interface {','type SendService interface {\n\tCentralFlow(action string, raw json.RawMessage, instance *instance_model.Instance) (any,error)'),
 'pkg/sendMessage/handler/send_handler.go':('type SendHandler interface {','type SendHandler interface {\n\tCentralFlow(ctx *gin.Context)'),
 'pkg/routes/routes.go':('eng.GET("/server/ok", r.serverHandler.ServerOk)','eng.GET("/server/ok", r.serverHandler.ServerOk)\n\tcentralflow := eng.Group("/centralflow",r.authMiddleware.Auth)\n\tcentralflow.GET("/*action",r.sendHandler.CentralFlow)\n\tcentralflow.POST("/*action",r.sendHandler.CentralFlow)'),
}
for path,(old,new) in targets.items():
 body=(root/path).read_bytes()
 if hashlib.sha256(body).hexdigest()!=manifest['sha256'][path]:raise SystemExit('Unsupported GO source: '+path)
 if body.decode().count(old)!=1:raise SystemExit('Source anchor changed: '+path)
sdk=root/'vendor/go.mau.fi/whatsmeow'
if not (sdk/'newsletter.go').is_file():raise SystemExit('Run go mod vendor before this installer')
if hashlib.sha256((sdk/'newsletter.go').read_bytes()).hexdigest()!=manifest['whatsmeow_newsletter_sha256']:raise SystemExit('Unsupported WhatsMeow dependency')
for path,(old,new) in targets.items():
 p=root/path;p.write_text(p.read_text().replace(old,new),encoding='utf-8',newline='\n')
for source,destination in [('centralflow.service.go','pkg/sendMessage/service/centralflow.go'),('centralflow.handler.go','pkg/sendMessage/handler/centralflow.go'),('centralflow.whatsmeow.go','vendor/go.mau.fi/whatsmeow/centralflow.go')]:
 shutil.copyfile(bundle/source,root/destination)
print('CentralFlow GO applied to verified source; native authentication preserved')
