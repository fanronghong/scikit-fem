"""
Author: gdmcbain.

Here's another extension of examples/ex01.py, still solving the Laplace
equation but now with mixed boundary conditions, two parts isopotential
(charged and earthed) and the rest insulated. The isopotential parts are
tagged during the construction of the geometry in pygmsh, as introduced in
ex12.py.

The example is ∇²u = 0 in Ω = {(x, y) : 1 < x² + y² < 4, 0 < θ < π/2},
where tan θ = y/x, with u = 0 on y = 0 and u = 1 on x = 0. Although these
boundaries would be simple enough to identify using the coordinates and
skfem.assembly.find_dofs as in ex03.py, the present technique generalizes to
more complicated shapes.

The exact solution is u = 2 θ / π. The field strength is |∇ u|² = 4/π² (x² + y²)
so the conductance (for unit potential difference and conductivity) is
‖∇ u‖² = 2 ln 2 / π.
"""

from skfem import *
from skfem.models.poisson import laplace, mass

import numpy as np

import meshio
from pygmsh import generate_mesh
from pygmsh.built_in import Geometry

geom = Geometry()
points = []
lines = []
radii = [1., 2.]
lcar = .1
points.append(geom.add_point([0.] * 3, lcar))  # centre
for x in radii:
    points.append(geom.add_point([x, 0., 0.], lcar))
for y in reversed(radii):
    points.append(geom.add_point([0., y, 0.], lcar))
lines.append(geom.add_line(*points[1:3]))
geom.add_physical_line(lines[-1], 'ground')
lines.append(geom.add_circle_arc(points[2], points[0], points[3]))
lines.append(geom.add_line(points[3], points[4]))
geom.add_physical_line(lines[-1], 'positive')
lines.append(geom.add_circle_arc(points[4], points[0], points[1]))
geom.add_physical_surface(
    geom.add_plane_surface(geom.add_line_loop(lines)), 'domain')

mesh = MeshTri.from_meshio(meshio.Mesh(*generate_mesh(geom,
                                                      prune_vertices=False)))

elements = ElementTriP1()
basis = InteriorBasis(mesh, elements, MappingAffine(mesh), 2)
A = asm(laplace, basis)

boundary_dofs = basis.get_dofs(mesh.boundaries)
interior_dofs = basis.complement_dofs(boundary_dofs)

u = np.zeros(basis.N)
u[boundary_dofs['positive'].all()] = 1.
u[interior_dofs] = solve(*condense(A, 0.*u, u, interior_dofs))

u_exact = 2 * np.arctan2(mesh.p[1, :], mesh.p[0, :]) / np.pi
u_error = u - u_exact
print('L2 error =', np.sqrt(u_error @ asm(mass, basis) @ u_error))
print('conductance = {:.4f} (exact = 2 ln 2 / pi = {:.4f})'.format(
    u @ A @ u, 2 * np.log(2) / np.pi))

@linear_form
def port_flux(v, dv, w):
    return sum(w.n * dv)

for port in mesh.boundaries:
    basis = FacetBasis(mesh, elements, facets=mesh.boundaries[port])
    form = asm(port_flux, basis)
    print('Current in through {} = {:.4f}'.format(port, form @ u))

mesh.plot(u)
mesh.show()
