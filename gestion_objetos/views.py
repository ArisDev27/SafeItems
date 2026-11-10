from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ObjetoForm

def inicio(request):
    return render(request, 'gestion_objetos/index.html')

@login_required(login_url='/admin/login/') # Pide sesión. Si no hay, lo manda al login temporal del admin.
def reportar_perdido(request):
    if request.method == 'POST':
        # request.FILES es vital para que Django pueda procesar la imagen subida
        form = ObjetoForm(request.POST, request.FILES) 
        if form.is_valid():
            objeto = form.save(commit=False) # Pausamos el guardado en la base de datos
            objeto.estado = 'PERDIDO' # Quemamos el estado para que siempre sea "PERDIDO"
            objeto.reportado_por = request.user # Asociamos el objeto al usuario que está en sesión
            objeto.save() # Ahora sí, guardamos todo en MySQL
            return redirect('inicio') # Lo devolvemos a la pantalla principal
    else:
        form = ObjetoForm()
    
    return render(request, 'gestion_objetos/reportar_perdido.html', {'form': form})