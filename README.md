# Practica-Maekawa
Práctica 4 Arquitecturas Avanzadas

El objetivo de esta práctica es, a partir del código dado, implementar el algoritmo de Maekawa para asegurar la exclusión mutua en la sección crítica.
Dicho algoritmo se encuentra explicado en: https://en.wikipedia.org/wiki/Maekawa%27s_algorithm

A grandes rasgos, se quiere conseguir el acceso a la sección crítica a través del consenso entre diferentes grupos a base de votos.
Cada proceso tendrá principalmente 3 estados: 
 - Request: Quiere acceder a la sección crítica
 - Held: Está en la sección crítica
 - Release: Sale de la sección crítica
 Cuando el estado de un proceso sea request, este pedirá a todos sus vecinos, que serán un subconjunto del total de nodos, que le den permiso.
 Si todo el grupo de vecinos le dice que puede entrar. El estado de este proceso pasará a ser held. A continuación, release y comunicará a todos sus vecinos que libera
 la sección crítica. Una vez hecho esto, volverá a empezar el ciclo.

Como posible mejora sería interesante desarrollar un algoritmo de asignación de vecinos en función del número de nodos, 
ya que actualmente está implementado manualmente solo para 3 o 7 nodos, para evitar posibles deadlocks.

**References**
- https://github.com/yvetterowe/Maekawa-Mutex
